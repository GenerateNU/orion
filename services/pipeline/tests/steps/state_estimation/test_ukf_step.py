import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.state import PX, PY, V
from orion_pipeline.steps.state_estimation.ukf_step import Tick, UKFStep

T0 = pd.Timestamp("2026-01-01")
LAT0, LON0 = 42.34, -71.09
# Written out instead of imported, so a wrong constant in the code gets caught
METERS_PER_DEGREE_LAT = 111_320.0
MPS_PER_MPH = 0.44704


def gps(ms: float, x: float, y: float) -> tuple:
    """A GPS reading ms after T0, at x m east and y m north of (LAT0, LON0)."""
    lat = LAT0 + y / METERS_PER_DEGREE_LAT
    lon = LON0 + x / (METERS_PER_DEGREE_LAT * np.cos(np.radians(LAT0)))
    return (T0 + pd.Timedelta(milliseconds=ms), "gps_location", [lat, lon])


def speed(ms: float, mps: float) -> tuple:
    """A speed reading ms after T0. The car reports mph."""
    return (T0 + pd.Timedelta(milliseconds=ms), "vcu_speed", [mps / MPS_PER_MPH])


def readings(*rows: tuple) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["time", "sensor", "values"])
    return df.sort_values(["time", "sensor"], ignore_index=True)


def run(df: pd.DataFrame, chunk: int | None = None) -> list[Tick]:
    """Push df through a fresh UKFStep in chunks of `chunk` rows, then flush."""
    ukf = UKFStep()
    chunk = chunk or len(df)
    ticks = []
    for start in range(0, len(df), chunk):
        ticks += ukf.push(df.iloc[start : start + chunk])
    return ticks + ukf.flush()


# Fixes at 0 and 200 ms, 3 m apart heading east: the filter starts at 200 ms
# with v = 3 m / 0.2 s = 15 m/s
START = (gps(0, 0, 0), gps(200, 3, 0))


def test_starts_from_two_fixes():
    # The fix at 100 ms is under 2 m from the first, so it can't start the filter
    ticks = run(readings(gps(0, 0, 0), gps(100, 1, 0), gps(200, 3, 0)))

    assert len(ticks) == 1
    tick = ticks[0]
    assert tick.time == T0 + pd.Timedelta(milliseconds=200)
    # Speed is measured from the first fix, not the one 1 m away
    np.testing.assert_allclose(tick.x, [3, 0, 15, 0, 0, 0], atol=1e-6)
    assert tick.x_pred is None and tick.p_pred is None and tick.cross_cov is None


def test_ticks_with_no_readings_still_predict():
    ticks = run(readings(*START, speed(250, 15)))

    times = [t.time for t in ticks]
    assert times == [T0 + pd.Timedelta(milliseconds=ms) for ms in range(200, 260, 10)]
    assert all(t.x_pred is not None for t in ticks[1:])


def test_gap_restarts_filter():
    # 1.5 s gap after the start: no ticks across it, then a fresh start
    ticks = run(readings(*START, gps(1700, 25, 0), gps(1900, 28, 0)))

    assert [t.time for t in ticks] == [
        T0 + pd.Timedelta(milliseconds=200),
        T0 + pd.Timedelta(milliseconds=1900),
    ]
    restart = ticks[1]
    assert restart.x_pred is None
    np.testing.assert_allclose(restart.x[[PX, PY, V]], [28, 0, 15], atol=1e-6)


def test_outlier_gps_is_ignored():
    tick = run(readings(*START, gps(210, 100, 0)))[-1]

    np.testing.assert_array_equal(tick.x, tick.x_pred)


def test_speed_is_converted_from_mph():
    # The filter predicts 15 m/s, and a 16 m/s reading (35.8 mph) should pull it
    # up. Read as 35.8 m/s instead, it would be gated and leave the speed at 15.
    tick = run(readings(*START, speed(210, 16)))[-1]

    assert tick.x_pred is not None
    assert tick.x_pred[V] < tick.x[V] < 16


def drive_readings(seed: int = 0) -> pd.DataFrame:
    """~4 s at 15 m/s, heading 30 deg, with noise, jittered times and a 1.5 s gap."""
    rng = np.random.default_rng(seed)
    heading = np.radians(30)
    rows = []
    for ms in range(0, 4000, 10):
        if 1500 <= ms < 3000:
            continue
        t = ms + rng.uniform(0, 9)
        d = 15 * t / 1000
        if ms % 100 == 0:
            x, y = d * np.cos(heading), d * np.sin(heading)
            rows.append(gps(t, *(np.array([x, y]) + rng.normal(0, 1, 2))))
        if ms % 20 == 0:
            rows.append(speed(t, 15 + rng.normal(0, 0.5)))
    return readings(*rows)


def test_chunk_size_does_not_change_ticks():
    df = drive_readings()
    expected = run(df)
    ticks = run(df, chunk=7)

    assert len(expected) > 100
    assert len(ticks) == len(expected)
    for got, want in zip(ticks, expected, strict=True):
        assert got.time == want.time
        for field in ("x", "p", "x_pred", "p_pred", "cross_cov"):
            a, b = getattr(got, field), getattr(want, field)
            if b is None:
                assert a is None
            else:
                np.testing.assert_array_equal(a, b)
