"""The GPS lag tracker on synthetic runs with a KNOWN, changing delay.

Fallbacks for no VCU / a parked run, paging and same-packet shifts are tested
through CleanStep in test_clean_step.py.
"""

import numpy as np

from orion_pipeline.steps.clean_step.gps_lag import (
    LagTrackerConfig,
    Segment,
    _reference_at,
    apply_fallbacks,
    lag_at,
    track_gps_lag,
)


def errors_away_from_changes(
    segments, gps_t, true_lag, measured_t, changes, margin=30.0
):
    far = np.ones(len(measured_t), dtype=bool)
    for c in changes:
        far &= np.abs(measured_t - c) > margin
    return np.abs(lag_at(gps_t, segments) - true_lag)[far]


def test_recovers_changing_lag(make_run):
    """1 s -> (3 min outage) -> 6 s -> (1 min outage) -> 11 s -> 4 s with NO long stamped gap.

    The last change happens because 8 s of measurements were dropped, so in stamped time
    there is only ~1 s of silence. The tracker must find it anyway (no gap assumption).
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


def test_corrected_order_is_kept(make_run):
    """Inside and between measured segments, corrected GroundSpeed times stay in order."""
    schedule = [(0, 1.0), (500, 6.0), (950, 11.0), (1400, 4.0)]
    outages = [(320, 500), (890, 950), (1392, 1400)]
    vcu_t, vcu, gps_t, gps, _, _ = make_run(1, schedule, outages, duration=1900)
    segs = track_gps_lag(vcu_t, vcu, gps_t, gps).segments
    seg = np.searchsorted([s.start_t for s in segs], gps_t, side="right") - 1
    ok = np.array([segs[i].quality == "ok" for i in seg])
    d = np.diff(gps_t - lag_at(gps_t, segs))
    assert (d[ok[1:] & ok[:-1]] >= -1e-9).all()


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


def test_unreliable_segment_uses_nearest_good_segment():
    segs = [
        Segment(0, 100, 1.0, 0.9, 1.1, 400, 300, "ok"),
        Segment(110, 150, 9.0, np.nan, np.nan, 40, 5, "unreliable"),
        Segment(400, 900, 6.0, 5.9, 6.1, 2000, 1500, "ok"),
    ]
    new = apply_fallbacks(segs, default_lag_s=3.0)
    assert [s.quality for s in new] == ["ok", "fallback", "ok"]
    assert [s.lag_s for s in new] == [1.0, 1.0, 6.0]  # segment 0 is closer than 2


def test_all_unreliable_uses_default():
    segs = [Segment(0, 100, 5.0, np.nan, np.nan, 40, 3, "unreliable")]
    new = apply_fallbacks(segs, default_lag_s=3.0)
    assert [(s.quality, s.lag_s) for s in new] == [("default", 3.0)]


def test_reference_at_first_vcu_sample_is_inside():
    """A query exactly on the first VCU timestamp has a reference (it used to be
    treated as outside the VCU range)."""
    _, width = _reference_at(
        np.array([0.0, 1.0, 2.0]), np.zeros(3), np.array([-0.5, 0.0, 2.0, 2.5])
    )
    assert list(width) == [np.inf, 1.0, 1.0, np.inf]
