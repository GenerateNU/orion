from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.state import STATE_SIZE, THETA, wrap_angle
from orion_pipeline.steps.state_estimation.ukf_step import Tick


def _is_startup(tick: Tick) -> bool:
    """A startup tick has no prediction linking it to the tick before it."""
    return tick.x_pred is None or tick.p_pred is None or tick.c is None


def _stack_or_empty(
    arrays: list[np.ndarray], empty_shape: tuple[int, ...]
) -> np.ndarray:
    """Stack arrays into one float64 array, or an empty one of empty_shape."""
    return np.stack(arrays).astype(np.float64) if arrays else np.empty(empty_shape)


@dataclass(frozen=True)
class ForwardPass:
    """One unbroken segment of UKF output, with N ticks.

    states (N, 6), covariances (N, 6, 6): filtered state and covariance at
    each tick.
    predicted_states (N-1, 6), predicted_covariances (N-1, 6, 6),
    cross_covariances (N-1, 6, 6): index k holds the prediction from tick k
    into tick k+1.
    """

    states: np.ndarray
    covariances: np.ndarray
    predicted_states: np.ndarray
    predicted_covariances: np.ndarray
    cross_covariances: np.ndarray

    def __post_init__(self) -> None:
        shape = np.shape(self.states)
        if len(shape) != 2 or shape[0] < 1 or shape[1] != STATE_SIZE:
            raise ValueError(
                f"states must have shape (N, {STATE_SIZE}) with N >= 1, got {shape}"
            )
        tick_count = shape[0]
        expected_shapes = {
            "covariances": (tick_count, STATE_SIZE, STATE_SIZE),
            "predicted_states": (tick_count - 1, STATE_SIZE),
            "predicted_covariances": (tick_count - 1, STATE_SIZE, STATE_SIZE),
            "cross_covariances": (tick_count - 1, STATE_SIZE, STATE_SIZE),
        }
        for name, expected in expected_shapes.items():
            actual = np.shape(getattr(self, name))
            if actual != expected:
                raise ValueError(f"{name} must have shape {expected}, got {actual}")
        for name in ("states", *expected_shapes):
            if not np.all(np.isfinite(getattr(self, name))):
                raise ValueError(f"{name} contains non-finite values")

    @classmethod
    def from_ticks(cls, ticks: Sequence[Tick]) -> "ForwardPass":
        """Build from one segment's recorded ticks.

        The UKF stores each prediction on tick k+1; this moves it to index k.
        The first tick's own prediction fields (None for a startup tick) are
        ignored. Every later tick must have one, so a segment cannot contain a
        restart: split the ticks at each startup tick first.
        """
        if not ticks:
            raise ValueError("A forward pass needs at least one tick.")

        predicted_states: list[np.ndarray] = []
        predicted_covariances: list[np.ndarray] = []
        cross_covariances: list[np.ndarray] = []
        for index, tick in enumerate(ticks[1:], start=1):
            if tick.x_pred is None or tick.p_pred is None or tick.c is None:
                raise ValueError(
                    f"Tick {index} has no prediction; "
                    "a segment cannot contain a restart."
                )
            predicted_states.append(tick.x_pred)
            predicted_covariances.append(tick.p_pred)
            cross_covariances.append(tick.c)

        size = STATE_SIZE
        return cls(
            states=_stack_or_empty([t.x for t in ticks], (0, size)),
            covariances=_stack_or_empty([t.p for t in ticks], (0, size, size)),
            predicted_states=_stack_or_empty(predicted_states, (0, size)),
            predicted_covariances=_stack_or_empty(
                predicted_covariances, (0, size, size)
            ),
            cross_covariances=_stack_or_empty(cross_covariances, (0, size, size)),
        )


@dataclass(frozen=True)
class SmoothedTick:
    """The smoothed state at one tick."""

    time: pd.Timestamp
    state: np.ndarray
    covariance: np.ndarray


def _split_at_restarts(ticks: Sequence[Tick]) -> Iterator[list[Tick]]:
    """Split ticks at each startup tick."""
    segment: list[Tick] = []
    for tick in ticks:
        if _is_startup(tick) and segment:
            yield segment
            segment = []
        segment.append(tick)
    if segment:
        yield segment


class URTS:
    """Unscented Rauch-Tung-Striebel smoother over UKF output."""

    @staticmethod
    def smooth_one_tick(
        state: np.ndarray,
        covariance: np.ndarray,
        predicted_state: np.ndarray,
        predicted_covariance: np.ndarray,
        cross_covariance: np.ndarray,
        next_smoothed_state: np.ndarray,
        next_smoothed_covariance: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """One RTS step: pull tick k toward the smoothed tick k+1."""
        gain = np.linalg.solve(predicted_covariance, cross_covariance.T).T

        residual = next_smoothed_state - predicted_state
        residual[THETA] = wrap_angle(residual[THETA])

        smoothed_state = state + gain @ residual
        smoothed_state[THETA] = wrap_angle(smoothed_state[THETA])

        smoothed_covariance = (
            covariance
            + gain @ (next_smoothed_covariance - predicted_covariance) @ gain.T
        )
        return smoothed_state, (smoothed_covariance + smoothed_covariance.T) / 2

    @classmethod
    def smooth_segment(cls, forward_pass: ForwardPass) -> tuple[np.ndarray, np.ndarray]:
        """Smooth one unbroken segment. The last tick comes back unchanged."""
        states = forward_pass.states.copy()
        covariances = forward_pass.covariances.copy()

        for k in range(len(states) - 2, -1, -1):
            states[k], covariances[k] = cls.smooth_one_tick(
                forward_pass.states[k],
                forward_pass.covariances[k],
                forward_pass.predicted_states[k],
                forward_pass.predicted_covariances[k],
                forward_pass.cross_covariances[k],
                states[k + 1],
                covariances[k + 1],
            )
        return states, covariances

    @classmethod
    def smooth_ticks(cls, ticks: Sequence[Tick]) -> list[SmoothedTick]:
        """Smooth a whole run, restarts included, one SmoothedTick per tick."""
        smoothed_ticks: list[SmoothedTick] = []
        for segment in _split_at_restarts(ticks):
            states, covariances = cls.smooth_segment(ForwardPass.from_ticks(segment))
            smoothed_ticks.extend(
                SmoothedTick(tick.time, states[i], covariances[i])
                for i, tick in enumerate(segment)
            )
        return smoothed_ticks
