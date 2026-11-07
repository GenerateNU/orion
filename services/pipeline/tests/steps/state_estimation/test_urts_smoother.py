import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.steps.state_estimation.state import PX, PY, STATE_SIZE, THETA
from orion_pipeline.steps.state_estimation.state_model_config import UnitConversions
from orion_pipeline.steps.state_estimation.ukf_step import Tick, UKFStep
from orion_pipeline.steps.state_estimation.urts_smoother import URTS, ForwardPass

S = STATE_SIZE
EYE = np.eye(S)
T0 = pd.Timestamp("2026-01-01 12:00:00")


def at(k: int) -> pd.Timestamp:
    return T0 + pd.Timedelta(milliseconds=10 * k)


def start_tick(k: int, x: float = 0.0) -> Tick:
    return Tick(at(k), np.full(S, x), EYE.copy(), None, None, None)


def linked_tick(k: int, x: float, p: float) -> Tick:
    """A tick predicted from the one before: x_pred 0, P_pred 2I, C = I."""
    return Tick(at(k), np.full(S, x), p * EYE, np.zeros(S), 2 * EYE, EYE.copy())


def chain() -> ForwardPass:
    """Three ticks whose smoothed values are easy to work out by hand."""
    return ForwardPass(
        states=np.array([np.full(S, 0.0), np.full(S, 1.0), np.full(S, 2.0)]),
        covariances=np.array([EYE, 1.5 * EYE, 1.5 * EYE]),
        predicted_states=np.zeros((2, S)),
        predicted_covariances=np.array([2 * EYE, 2 * EYE]),
        cross_covariances=np.array([EYE, EYE]),
    )


def test_forward_pass_rejects_bad_shapes_and_non_finite_values() -> None:
    fp = chain()
    with pytest.raises(ValueError, match="predicted_states"):
        replace(fp, predicted_states=np.zeros((3, S)))  # should be N-1 = 2
    with pytest.raises(ValueError, match="shape"):
        replace(fp, covariances=np.zeros((1, 1, 1)))
    for field in ("states", "cross_covariances"):
        for bad in (np.nan, np.inf):
            arr = getattr(fp, field).copy()
            arr.flat[0] = bad
            with pytest.raises(ValueError, match="non-finite"):
                replace(fp, **{field: arr})


def test_from_ticks_moves_each_prediction_back_one_index() -> None:
    t1 = replace(linked_tick(1, 1.0, 1.5), x_pred=np.full(S, 10.0))
    t2 = replace(linked_tick(2, 2.0, 1.5), x_pred=np.full(S, 20.0))
    fp = ForwardPass.from_ticks([start_tick(0), t1, t2])

    assert fp.states.shape == (3, S) and fp.predicted_states.shape == (2, S)
    # Index k holds the prediction INTO tick k+1
    np.testing.assert_array_equal(fp.predicted_states[0], np.full(S, 10.0))
    np.testing.assert_array_equal(fp.predicted_states[1], np.full(S, 20.0))


def test_from_ticks_rejects_a_restart_inside_the_segment() -> None:
    with pytest.raises(ValueError, match="restart"):
        ForwardPass.from_ticks([start_tick(0), start_tick(1)])


def test_smooth_step_wraps_the_heading() -> None:
    # Residual: really 0.0832 rad across +/- pi, not -6.2
    x_pred = np.zeros(S)
    x_pred[THETA] = 3.1
    x_next = np.zeros(S)
    x_next[THETA] = -3.1
    x, _ = URTS.smooth_one_tick(
        np.zeros(S), EYE, x_pred, 2 * EYE, EYE, x_next, 1.5 * EYE
    )
    assert x[THETA] == pytest.approx(0.5 * (-6.2 + 2 * math.pi))

    # Result: 3.0 + 0.5 * 3.0 = 4.5 wraps back into [-pi, pi]
    x = np.zeros(S)
    x[THETA] = 3.0
    x_next = np.zeros(S)
    x_next[THETA] = 3.0
    out, _ = URTS.smooth_one_tick(x, EYE, np.zeros(S), 2 * EYE, EYE, x_next, 1.5 * EYE)
    assert out[THETA] == pytest.approx(4.5 - 2 * math.pi)


def test_smooth_step_keeps_covariance_exactly_symmetric() -> None:
    rng = np.random.default_rng(0)

    def spd() -> np.ndarray:
        a = rng.normal(size=(S, S))
        return a @ a.T + S * EYE

    _, P = URTS.smooth_one_tick(
        rng.normal(size=S),
        spd(),
        rng.normal(size=S),
        spd(),
        rng.normal(size=(S, S)),
        rng.normal(size=S),
        spd(),
    )
    assert np.array_equal(P, P.T)


def test_urts_class_smooths_each_segment_separately() -> None:
    # Tick 2 restarted the filter, so ticks 2 and 3 never touch ticks 0 and 1
    ticks = [
        start_tick(0),
        linked_tick(1, 1.0, 1.5),
        start_tick(2, 1.0),
        linked_tick(3, 2.0, 1.5),
    ]
    out = URTS.smooth_ticks(ticks)

    assert [s.time for s in out] == [t.time for t in ticks]
    np.testing.assert_array_equal(out[1].state, ticks[1].x)  # end of segment 1
    np.testing.assert_allclose(out[0].state, np.full(S, 0.5))
    np.testing.assert_array_equal(out[3].state, ticks[3].x)  # end of segment 2
    np.testing.assert_allclose(out[2].state, np.full(S, 2.0))  # 1 + 0.5 * (2 - 0)
    assert URTS.smooth_ticks([]) == []


def drive(
    t_start_ms: int, t_end_ms: int, rng: np.random.Generator
) -> tuple[list[tuple[int, str, list[float]]], dict[int, np.ndarray]]:
    """Noisy GPS (10 Hz) and speed (20 Hz) for a car circling at 10 m/s.

    Returns the readings and the true [x, y] in meters at every 10 ms tick.
    """
    m_per_deg = UnitConversions.METERS_PER_DEGREE_LAT
    cos_lat = math.cos(math.radians(42.0))
    radius, speed = 30.0, 10.0

    def true_xy(t_ms: int) -> np.ndarray:
        a = speed * t_ms / 1000 / radius
        return np.array([radius * math.sin(a), radius * (1 - math.cos(a))])

    truth = {t: true_xy(t) for t in range(t_start_ms, t_end_ms + 1, 10)}
    rows: list[tuple[int, str, list[float]]] = []
    for t in range(t_start_ms, t_end_ms + 1, 50):
        if t % 100 == 0:
            x, y = truth[t] + rng.normal(0, 1.5, 2)
            rows.append(
                (
                    t,
                    "gps_location",
                    [42.0 + y / m_per_deg, -71.0 + x / (m_per_deg * cos_lat)],
                )
            )
        v = speed + rng.normal(0, 0.5)
        rows.append((t, "vcu_speed", [v / UnitConversions.MPS_PER_MPH]))
    return rows, truth


def to_frame(rows: list[tuple[int, str, list[float]]]) -> pd.DataFrame:
    rows = sorted(rows, key=lambda r: r[0])
    return pd.DataFrame(
        {
            "time": [T0 + pd.Timedelta(milliseconds=t) for t, _, _ in rows],
            "sensor": [s for _, s, _ in rows],
            "values": [v for _, _, v in rows],
        }
    )


def rmse(xs: np.ndarray, truth: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum((xs[:, [PX, PY]] - truth) ** 2, axis=1))))


def test_smoothing_beats_filtering_against_known_truth() -> None:
    rows, truth = drive(0, 20_000, np.random.default_rng(1))
    ukf = UKFStep()
    ticks = ukf.push(to_frame(rows)) + ukf.flush()
    assert ukf.origin is not None

    # The filter's local frame starts at its first GPS fix, not at the true start
    m_per_deg = UnitConversions.METERS_PER_DEGREE_LAT
    ox = (ukf.origin[1] + 71.0) * m_per_deg * math.cos(math.radians(42.0))
    oy = (ukf.origin[0] - 42.0) * m_per_deg
    ref = np.array(
        [truth[round((t.time - T0).total_seconds() * 1000)] - [ox, oy] for t in ticks]
    )

    fp = ForwardPass.from_ticks(ticks)
    xs, _ = URTS.smooth_segment(fp)
    # Skip the first second, where the filter is still settling
    settled = slice(100, None)
    filtered_err = rmse(fp.states[settled], ref[settled])
    smoothed_err = rmse(xs[settled], ref[settled])
    assert smoothed_err < filtered_err


def test_urts_class_on_ukf_output_with_a_restart() -> None:
    rng = np.random.default_rng(2)
    first, _ = drive(0, 8_000, rng)
    # A 3 s silence is past max_gap (1 s), so the filter restarts afterwards
    second, _ = drive(11_000, 19_000, rng)
    ukf = UKFStep()
    ticks = ukf.push(to_frame(first + second)) + ukf.flush()

    startups = [i for i, t in enumerate(ticks) if t.x_pred is None]
    assert len(startups) == 2 and startups[0] == 0

    out = URTS.smooth_ticks(ticks)

    assert [s.time for s in out] == [t.time for t in ticks]
    assert all(
        np.all(np.isfinite(s.state)) and np.all(np.isfinite(s.covariance)) for s in out
    )
    # Each segment's last tick is unchanged, and the first moved
    seg_ends = [startups[1] - 1, len(ticks) - 1]
    for i in seg_ends:
        np.testing.assert_array_equal(out[i].state, ticks[i].x)
    for i in startups:
        assert not np.array_equal(out[i].state, ticks[i].x)


def test_smooth_frame_matches_smooth_ticks():
    rng = np.random.default_rng(0)
    ticks = []
    for i in range(8):
        x, p = rng.normal(size=6), np.eye(6)
        startup = i in (0, 4)
        pred = (None, None, None) if startup else (x + 0.1, 1.5 * p, 0.5 * p)
        ticks.append(
            Tick(
                pd.Timestamp("2026-01-01") + pd.Timedelta(milliseconds=10 * i),
                x,
                p,
                *pred,
            )
        )

    frame = URTS.smooth_frame(pd.DataFrame(ticks))

    expected = URTS.smooth_ticks(ticks)
    assert list(frame["time"]) == [t.time for t in expected]
    np.testing.assert_allclose(
        np.stack(frame["x_smooth"]), np.stack([t.state for t in expected])
    )
    np.testing.assert_allclose(
        np.stack(frame["p_smooth"]), np.stack([t.covariance for t in expected])
    )
