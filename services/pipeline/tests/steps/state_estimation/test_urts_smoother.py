import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.steps.state_estimation.state import STATE_SIZE, THETA
from orion_pipeline.steps.state_estimation.state_model_config import UnitConversions
from orion_pipeline.steps.state_estimation.ukf_step import Tick, UKFStep
from orion_pipeline.steps.state_estimation.urts_smoother import (
    URTS,
    ForwardPass,
    smooth_step,
    urts_smooth,
)

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
        xs=np.array([np.full(S, 0.0), np.full(S, 1.0), np.full(S, 2.0)]),
        Ps=np.array([EYE, 1.5 * EYE, 1.5 * EYE]),
        x_preds=np.zeros((2, S)),
        P_preds=np.array([2 * EYE, 2 * EYE]),
        Cs=np.array([EYE, EYE]),
    )


def test_forward_pass_rejects_bad_shapes_and_non_finite_values() -> None:
    fp = chain()
    with pytest.raises(ValueError, match="x_preds"):
        replace(fp, x_preds=np.zeros((3, S)))  # should be N-1 = 2
    with pytest.raises(ValueError, match="shape"):
        replace(fp, Ps=np.zeros((1, 1, 1)))
    for field in ("xs", "Cs"):
        for bad in (np.nan, np.inf):
            arr = getattr(fp, field).copy()
            arr.flat[0] = bad
            with pytest.raises(ValueError, match="non-finite"):
                replace(fp, **{field: arr})


def test_from_ticks_moves_each_prediction_back_one_index() -> None:
    t1 = replace(linked_tick(1, 1.0, 1.5), x_pred=np.full(S, 10.0))
    t2 = replace(linked_tick(2, 2.0, 1.5), x_pred=np.full(S, 20.0))
    fp = ForwardPass.from_ticks([start_tick(0), t1, t2])

    assert fp.xs.shape == (3, S) and fp.x_preds.shape == (2, S)
    # Index k holds the prediction INTO tick k+1
    np.testing.assert_array_equal(fp.x_preds[0], np.full(S, 10.0))
    np.testing.assert_array_equal(fp.x_preds[1], np.full(S, 20.0))


def test_from_ticks_rejects_a_restart_inside_the_segment() -> None:
    with pytest.raises(ValueError, match="restart"):
        ForwardPass.from_ticks([start_tick(0), start_tick(1)])


def test_smooth_step_known_answer_and_inputs_untouched() -> None:
    # G = C inv(P_pred) = 0.5 I
    # x = 0 + 0.5 * (1 - 0) = 0.5, P = 1 + 0.25 * (1.5 - 2) = 0.875
    args = [np.zeros(S), EYE.copy(), np.zeros(S), 2 * EYE, EYE.copy()]
    args += [np.ones(S), 1.5 * EYE]
    before = [a.copy() for a in args]

    x, P = smooth_step(*args)

    np.testing.assert_allclose(x, np.full(S, 0.5))
    np.testing.assert_allclose(P, 0.875 * EYE)
    for a, b in zip(args, before, strict=True):
        np.testing.assert_array_equal(a, b)


def test_smooth_step_wraps_the_heading() -> None:
    # Residual: really 0.0832 rad across +/- pi, not -6.2
    x_pred = np.zeros(S)
    x_pred[THETA] = 3.1
    x_next = np.zeros(S)
    x_next[THETA] = -3.1
    x, _ = smooth_step(np.zeros(S), EYE, x_pred, 2 * EYE, EYE, x_next, 1.5 * EYE)
    assert x[THETA] == pytest.approx(0.5 * (-6.2 + 2 * math.pi))

    # Result: 3.0 + 0.5 * 3.0 = 4.5 wraps back into [-pi, pi]
    x = np.zeros(S)
    x[THETA] = 3.0
    x_next = np.zeros(S)
    x_next[THETA] = 3.0
    out, _ = smooth_step(x, EYE, np.zeros(S), 2 * EYE, EYE, x_next, 1.5 * EYE)
    assert out[THETA] == pytest.approx(4.5 - 2 * math.pi)


def test_smooth_step_keeps_covariance_exactly_symmetric() -> None:
    rng = np.random.default_rng(0)

    def spd() -> np.ndarray:
        a = rng.normal(size=(S, S))
        return a @ a.T + S * EYE

    _, P = smooth_step(
        rng.normal(size=S),
        spd(),
        rng.normal(size=S),
        spd(),
        rng.normal(size=(S, S)),
        rng.normal(size=S),
        spd(),
    )
    assert np.array_equal(P, P.T)


def test_urts_smooth_known_answer_and_inputs_untouched() -> None:
    fp = chain()
    before = [a.copy() for a in (fp.xs, fp.Ps, fp.x_preds, fp.P_preds, fp.Cs)]

    xs, Ps = urts_smooth(fp)

    # Last tick unchanged
    np.testing.assert_array_equal(xs[2], np.full(S, 2.0))
    np.testing.assert_array_equal(Ps[2], 1.5 * EYE)
    # Tick 1: x = 1 + 0.5 * (2 - 0) = 2, P = 1.5 + 0.25 * (1.5 - 2) = 1.375
    np.testing.assert_allclose(xs[1], np.full(S, 2.0))
    np.testing.assert_allclose(Ps[1], 1.375 * EYE)
    # Tick 0 uses the smoothed tick 1: x = 0.5 * 2 = 1, P = 1 + 0.25 * (1.375 - 2)
    np.testing.assert_allclose(xs[0], np.full(S, 1.0))
    np.testing.assert_allclose(Ps[0], 0.84375 * EYE)

    after = (fp.xs, fp.Ps, fp.x_preds, fp.P_preds, fp.Cs)
    for a, b in zip(after, before, strict=True):
        np.testing.assert_array_equal(a, b)


def test_urts_class_smooths_each_segment_separately() -> None:
    # Tick 2 restarted the filter, so ticks 2 and 3 never touch ticks 0 and 1
    ticks = [
        start_tick(0),
        linked_tick(1, 1.0, 1.5),
        start_tick(2, 1.0),
        linked_tick(3, 2.0, 1.5),
    ]
    out = URTS().smooth(ticks)

    assert [s.time for s in out] == [t.time for t in ticks]
    np.testing.assert_array_equal(out[1].x, ticks[1].x)  # end of segment 1
    np.testing.assert_allclose(out[0].x, np.full(S, 0.5))
    np.testing.assert_array_equal(out[3].x, ticks[3].x)  # end of segment 2
    np.testing.assert_allclose(out[2].x, np.full(S, 2.0))  # 1 + 0.5 * (2 - 0)
    assert URTS().smooth([]) == []


def test_smoothing_real_ukf_ticks_end_to_end() -> None:
    m_per_deg = UnitConversions.METERS_PER_DEGREE_LAT
    mps_per_mph = UnitConversions.MPS_PER_MPH

    def gps(x: float) -> list[float]:
        return [42.0, -71.0 + x / (m_per_deg * math.cos(math.radians(42.0)))]

    rows: list[tuple[int, str, list[float]]] = [
        (0, "gps_location", gps(0)),
        (100, "gps_location", gps(1)),
        (200, "gps_location", gps(3)),
    ]
    for t in range(250, 1000, 50):
        rows.append((t, "vcu_speed", [15.0 / mps_per_mph]))
        if t % 100 == 0:
            rows.append((t, "gps_location", gps(3 + 15 * (t - 200) / 1000)))
    rows.sort(key=lambda r: r[0])
    df = pd.DataFrame(
        {
            "time": [T0 + pd.Timedelta(milliseconds=t) for t, _, _ in rows],
            "sensor": [s for _, s, _ in rows],
            "values": [v for _, _, v in rows],
        }
    )

    ukf = UKFStep()
    ticks = ukf.push(df) + ukf.flush()
    fp = ForwardPass.from_ticks(ticks)
    xs, Ps = urts_smooth(fp)

    assert len(ticks) > 50 and xs.shape == fp.xs.shape
    assert np.all(np.isfinite(xs)) and np.all(np.isfinite(Ps))
    np.testing.assert_array_equal(xs[-1], fp.xs[-1])  # last tick unchanged
    assert not np.array_equal(xs[0], fp.xs[0])  # earlier ticks did move