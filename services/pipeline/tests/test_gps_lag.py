"""The sliding-window GPS lag estimator on synthetic runs with a KNOWN, changing delay.

Fallbacks for no VCU / a parked run, paging and same-packet shifts are tested
through CleanStep in test_clean_step.py.
"""

import numpy as np

from orion_pipeline.steps.clean_step.gps_lag import lag_at, track_gps_lag
from orion_pipeline.steps.clean_step.gps_lag_config import LagTrackerConfig

# A window straddling a jump sees both delays, so a jump is only located to within
# about half a window plus a hop.
JUMP_MARGIN_S = 45.0


def errors_away_from_changes(
    segments, gps_t, true_lag, measured_t, changes, margin=JUMP_MARGIN_S
):
    far = np.ones(len(measured_t), dtype=bool)
    for c in changes:
        far &= np.abs(measured_t - c) > margin
    return np.abs(lag_at(gps_t, segments) - true_lag)[far]


def test_recovers_changing_lag(make_run):
    """1 s -> (3 min outage) -> 6 s -> (1 min outage) -> 11 s -> 4 s with NO long stamped gap.

    The last change happens because 8 s of measurements were dropped, so in stamped time
    there is only ~1 s of silence. The window estimate must find it anyway.
    """
    schedule = [(0, 1.0), (500, 6.0), (950, 11.0), (1400, 4.0)]
    outages = [(320, 500), (890, 950), (1392, 1400)]
    vcu_t, vcu, gps_t, gps, true_lag, tm = make_run(1, schedule, outages, duration=1900)
    res = track_gps_lag(vcu_t, vcu, gps_t, gps)
    err = errors_away_from_changes(res.segments, gps_t, true_lag, tm, [500, 950, 1400])
    assert np.median(err) < 0.25, np.median(err)
    assert np.percentile(err, 95) < 0.6, np.percentile(err, 95)
    found = sorted(round(s.lag_s) for s in res.segments if s.quality == "ok")
    for expected in (1, 6, 11, 4):
        assert expected in found, (expected, found)


def test_dead_gps_stretch_does_not_create_fake_jumps(make_run):
    vcu_t, vcu, gps_t, gps, true_lag, _ = make_run(
        2, [(0, 2.0)], dead=[(600, 800)], duration=1500
    )
    res = track_gps_lag(vcu_t, vcu, gps_t, gps)
    assert np.percentile(np.abs(lag_at(gps_t, res.segments) - true_lag), 95) < 0.5


def test_low_scale_run(make_run):
    """One real run reads ~30% low (scale ~0.7). Lag must still be right and scale reported."""
    vcu_t, vcu, gps_t, gps, true_lag, _ = make_run(
        3, [(0, 1.5)], gps_scale=0.70, duration=1200
    )
    res = track_gps_lag(vcu_t, vcu, gps_t, gps)
    assert abs(res.scale - 0.70) < 0.05, res.scale
    assert np.median(np.abs(lag_at(gps_t, res.segments) - true_lag)) < 0.25


def test_no_gps_rows_uses_default():
    res = track_gps_lag([0, 1, 2], [0, 5, 10], [], [])
    assert [s.quality for s in res.segments] == ["default"]
    assert np.allclose(
        lag_at([10.0, 11.0], res.segments), LagTrackerConfig().default_lag_s
    )


def wavy_run(lag, duration=900.0, seed=0):
    """A car whose speed never holds still (20-50 mph, always changing), so every
    60 s window pins the delay down. GPS is stamped `lag` s late."""
    rng = np.random.default_rng(seed)

    def speed(t):
        return 35 + 12 * np.sin(2 * np.pi * t / 17) + 5 * np.sin(2 * np.pi * t / 6.3)

    vcu_t = np.cumsum(rng.exponential(0.3, int(duration / 0.3)))
    vcu_t = vcu_t[vcu_t < duration]
    measured = np.cumsum(rng.exponential(0.25, int(duration / 0.25)))
    measured = measured[measured < duration]
    gps = 0.94 * speed(measured) + rng.normal(0, 0.4, len(measured))
    return vcu_t, speed(vcu_t), measured + lag, gps


def test_constant_lag_is_recovered_in_every_window():
    vcu_t, vcu, gps_t, gps = wavy_run(lag=4.0)
    res = track_gps_lag(vcu_t, vcu, gps_t, gps)
    assert [s.quality for s in res.segments] == ["ok"]
    assert abs(res.segments[0].lag_s - 4.0) < 0.25, res.segments


def test_windows_with_a_data_gap_take_the_nearest_measured_lag():
    """A 40 s VCU outage leaves too little to judge; those hops are fallbacks."""
    vcu_t, vcu, gps_t, gps = wavy_run(lag=4.0)
    keep = (vcu_t < gps_t[0] + 70) | (vcu_t > gps_t[0] + 110)
    res = track_gps_lag(vcu_t[keep], vcu[keep], gps_t, gps)
    assert "fallback" in {s.quality for s in res.segments}
    assert np.allclose(lag_at(gps_t, res.segments), 4.0, atol=0.25)


def test_implausible_scale_gives_default_everywhere(make_run):
    vcu_t, vcu, gps_t, gps, _, _ = make_run(32, [(0, 2.0)], gps_scale=0.5, duration=900)
    res = track_gps_lag(vcu_t, vcu, gps_t, gps)
    assert res.scale < LagTrackerConfig().min_scale
    assert [(s.quality, s.lag_s) for s in res.segments] == [("default", 3.0)]


def test_too_few_measurable_windows_gives_default_everywhere(make_run):
    """Parked except for the last few seconds: almost nothing to measure from."""
    vcu_t, vcu, gps_t, gps, _, _ = make_run(33, [(0, 2.0)], duration=600)
    vcu = np.where(vcu_t < 595, 0.0, vcu)
    gps = np.where(gps_t < 597, 0.0, gps)
    res = track_gps_lag(vcu_t, vcu, gps_t, gps)
    assert [(s.quality, s.lag_s) for s in res.segments] == [("default", 3.0)]
