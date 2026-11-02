from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.state import STATE_SIZE, THETA, wrap_angle
from orion_pipeline.steps.state_estimation.ukf_step import Tick


@dataclass(frozen=True)
class ForwardPass:
    """One unbroken segment of UKF output, with N ticks.

    xs (N, 6), Ps (N, 6, 6): filtered state and covariance at each tick.
    x_preds (N-1, 6), P_preds (N-1, 6, 6), Cs (N-1, 6, 6): index k holds the
    prediction from tick k into tick k+1.
    """

    xs: np.ndarray
    Ps: np.ndarray
    x_preds: np.ndarray
    P_preds: np.ndarray
    Cs: np.ndarray

    def __post_init__(self) -> None:
        shape = np.shape(self.xs)
        if len(shape) != 2 or shape[0] < 1 or shape[1] != STATE_SIZE:
            raise ValueError(
                f"xs must have shape (N, {STATE_SIZE}) with N >= 1, got {shape}"
            )
        n_ticks, n = shape
        expected = {
            "Ps": (n_ticks, n, n),
            "x_preds": (n_ticks - 1, n),
            "P_preds": (n_ticks - 1, n, n),
            "Cs": (n_ticks - 1, n, n),
        }
        for name, want in expected.items():
            got = np.shape(getattr(self, name))
            if got != want:
                raise ValueError(f"{name} must have shape {want}, got {got}")
        for name in ("xs", *expected):
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

        x_preds: list[np.ndarray] = []
        P_preds: list[np.ndarray] = []
        Cs: list[np.ndarray] = []
        for k, tick in enumerate(ticks[1:], start=1):
            if tick.x_pred is None or tick.P_pred is None or tick.C is None:
                raise ValueError(
                    f"Tick {k} has no prediction; a segment cannot contain a restart."
                )
            x_preds.append(tick.x_pred)
            P_preds.append(tick.P_pred)
            Cs.append(tick.C)

        n = STATE_SIZE
        return cls(
            xs=np.stack([t.x for t in ticks]).astype(np.float64),
            Ps=np.stack([t.P for t in ticks]).astype(np.float64),
            x_preds=np.stack(x_preds).astype(np.float64)
            if x_preds
            else np.empty((0, n)),
            P_preds=np.stack(P_preds).astype(np.float64)
            if P_preds
            else np.empty((0, n, n)),
            Cs=np.stack(Cs).astype(np.float64) if Cs else np.empty((0, n, n)),
        )


def smooth_step(
    x: np.ndarray,
    P: np.ndarray,
    x_pred: np.ndarray,
    P_pred: np.ndarray,
    C: np.ndarray,
    x_next: np.ndarray,
    P_next: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """One RTS step: pull tick k toward the smoothed tick k+1.

    x, P: filtered state and covariance at tick k.
    x_pred, P_pred, C: the UKF's prediction from tick k into k+1.
    x_next, P_next: the smoothed state and covariance at tick k+1.
    Returns new arrays; the inputs are not modified.
    """
    # Smoother gain G = C @ inv(P_pred). P_pred is symmetric.
    G = np.linalg.solve(P_pred, C.T).T

    dx = x_next - x_pred
    dx[THETA] = wrap_angle(dx[THETA])

    x_smooth = x + G @ dx
    x_smooth[THETA] = wrap_angle(x_smooth[THETA])

    P_smooth = P + G @ (P_next - P_pred) @ G.T
    return x_smooth, (P_smooth + P_smooth.T) / 2


def urts_smooth(forward: ForwardPass) -> tuple[np.ndarray, np.ndarray]:
    """Smooth a forward pass. Returns (xs, Ps) with the same shapes as the input.

    The last tick has no future to learn from, so it comes back unchanged. The
    inputs are not modified.
    """
    xs = forward.xs.copy()
    Ps = forward.Ps.copy()

    for k in range(len(xs) - 2, -1, -1):
        xs[k], Ps[k] = smooth_step(
            forward.xs[k],
            forward.Ps[k],
            forward.x_preds[k],
            forward.P_preds[k],
            forward.Cs[k],
            xs[k + 1],
            Ps[k + 1],
        )
    return xs, Ps


@dataclass(frozen=True)
class SmoothedTick:
    """The smoothed state at one tick."""

    time: pd.Timestamp
    x: np.ndarray
    P: np.ndarray


class URTS:
    """Smooths a whole run of UKF ticks, restarts included.

    A thin wrapper over ForwardPass and urts_smooth. It splits the ticks into
    unbroken segments (a startup tick begins a new one), smooths each segment on
    its own, and returns one SmoothedTick per input tick, in order. Smoothing
    never crosses a restart. Needs all the ticks at once.
    """

    def smooth(self, ticks: Sequence[Tick]) -> list[SmoothedTick]:
        smoothed: list[SmoothedTick] = []
        for segment in self._segments(ticks):
            xs, Ps = urts_smooth(ForwardPass.from_ticks(segment))
            smoothed.extend(
                SmoothedTick(tick.time, xs[i], Ps[i]) for i, tick in enumerate(segment)
            )
        return smoothed

    @staticmethod
    def _segments(ticks: Sequence[Tick]) -> Iterator[list[Tick]]:
        """Split ticks at each startup tick (a tick with no prediction)."""
        segment: list[Tick] = []
        for tick in ticks:
            if tick.x_pred is None and segment:
                yield segment
                segment = []
            segment.append(tick)
        if segment:
            yield segment