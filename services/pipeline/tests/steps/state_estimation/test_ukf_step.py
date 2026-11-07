import numpy as np
import pandas as pd

from orion_pipeline.steps.state_estimation.state import OMEGA, PX, PY, THETA, V
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


# Fixes at 0 and 1000 ms, 15 m apart heading east: the filter starts at 1000 ms
# with v = 15 m / 1 s = 15 m/s
START = (gps(0, 0, 0), gps(1000, 15, 0))
GPS_STD_M = 1.5


def test_starts_from_two_fixes():
    # The fix at 500 ms is under 10 m from the first, so it can't start the filter
    ticks = run(readings(gps(0, 0, 0), gps(500, 7.5, 0), gps(1000, 15, 0)))

    assert len(ticks) == 1
    tick = ticks[0]
    assert tick.time == T0 + pd.Timedelta(milliseconds=1000)
    # Speed is measured from the first fix, not the one 7.5 m away
    np.testing.assert_allclose(tick.x, [15, 0, 15, 0, 0, 0], atol=1e-6)
    assert tick.x_pred is None and tick.p_pred is None and tick.cross_cov is None


def test_start_heading_uncertainty_comes_from_the_baseline():
    tick = run(readings(*START))[0]

    # Two fixes 15 m apart, each off by ~1.5 m: heading var 2 * 1.5^2 / 15^2
    np.testing.assert_allclose(tick.p[THETA, THETA], 2 * GPS_STD_M**2 / 15**2)


def test_stale_first_fix_is_replaced():
    # Parked GPS drifts 11 m over 6 s. That's past the 5 s limit, so the drift
    # doesn't start the filter; the 6 s fix becomes the new first fix instead
    ticks = run(readings(gps(0, 0, 0), gps(6000, 11, 0), gps(7000, 26, 0)))

    assert [t.time for t in ticks] == [T0 + pd.Timedelta(milliseconds=7000)]
    np.testing.assert_allclose(ticks[0].x[[PX, V]], [26, 15], atol=1e-6)


def test_ticks_with_no_readings_still_predict():
    ticks = run(readings(*START, speed(1050, 15)))

    times = [t.time for t in ticks]
    assert times == [T0 + pd.Timedelta(milliseconds=ms) for ms in range(1000, 1060, 10)]
    assert all(t.x_pred is not None for t in ticks[1:])


def test_gap_restarts_filter():
    # 1.5 s gap after the start: no ticks across it, then a fresh start
    ticks = run(readings(*START, gps(2500, 37.5, 0), gps(3500, 52.5, 0)))

    assert [t.time for t in ticks] == [
        T0 + pd.Timedelta(milliseconds=1000),
        T0 + pd.Timedelta(milliseconds=3500),
    ]
    restart = ticks[1]
    assert restart.x_pred is None
    np.testing.assert_allclose(restart.x[[PX, PY, V]], [52.5, 0, 15], atol=1e-6)


def test_far_gps_fix_is_still_applied():
    # GPS is ungated, so even a fix far from the prediction pulls the state
    # toward it; a gate here would lock a drifted filter out for good.
    tick = run(readings(*START, gps(1010, 100, 0)))[-1]

    assert tick.x_pred is not None
    assert tick.x_pred[PX] < tick.x[PX] < 100


def gyro(ms: float, yaw_radps: float) -> tuple:
    """A gyro reading ms after T0: yaw_radps of left turn, in mdps along the
    tilted board's axes, bias included."""
    up = np.array([-0.859, -0.037, 0.511])  # the mount's gravity direction
    mdps = (yaw_radps + 0.0075) * 180 / np.pi * 1000 * up / np.dot(up, up)
    return (T0 + pd.Timedelta(milliseconds=ms), "vcu_imu_gyro", list(mdps))


def test_gyro_pulls_turn_rate_toward_reading():
    tick = run(readings(*START, gyro(1010, 0.5)))[-1]

    assert tick.x_pred is not None
    assert tick.x_pred[OMEGA] < tick.x[OMEGA] < 0.5


def test_parked_gyro_reads_zero_turn_rate():
    # A reading of just the bias is no turn: OMEGA stays where it was predicted
    tick = run(readings(*START, gyro(1010, 0.0)))[-1]

    assert tick.x_pred is not None
    np.testing.assert_allclose(tick.x[OMEGA], 0.0, atol=1e-9)


def test_speed_is_converted_from_mph():
    # The filter predicts 15 m/s, and a 16 m/s reading (35.8 mph) should pull it
    # up. Read as 35.8 m/s instead, it would pull the speed past 16.
    tick = run(readings(*START, speed(1010, 16)))[-1]

    assert tick.x_pred is not None
    assert tick.x_pred[V] < tick.x[V] < 16


def test_far_speed_reading_is_still_applied():
    # Speed is ungated too: a reading far from the prediction still pulls it
    tick = run(readings(*START, speed(1010, 30)))[-1]

    assert tick.x_pred is not None
    assert tick.x_pred[V] < tick.x[V] < 30


def test_parked_speed_holds_speed_and_turn_rate_at_zero():
    # The gyro claims a turn, then the car reports it's stopped. The zero-speed
    # update pulls both speed and turn rate nearly all the way to 0, far more
    # than one 0.5 m/s-noise speed reading could on its own.
    tick = run(readings(*START, gyro(1010, 0.5), speed(1010, 0)))[-1]

    assert abs(tick.x[V]) < 0.5
    assert abs(tick.x[OMEGA]) < 0.05


def test_slow_but_moving_speed_is_not_held_at_zero():
    tick = run(readings(*START, gyro(1010, 0.5), speed(1010, 1)))[-1]

    assert tick.x[OMEGA] > 0.1


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
