"""CleanStep end to end on synthetic runs, with fake Penelope / OrionDB clients."""

from typing import cast

import numpy as np
import pandas as pd
import pytest

from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.clean_step.clean_step import CleanStep
from orion_pipeline.steps.clean_step.clean_utils import to_epoch_s
from orion_pipeline.steps.clean_step.gps_lag import MS_TO_MPH, Segment

RUN_ID = "synthetic-run"
T0 = 1.75e9  # epoch seconds of the run's start

SENSOR_MAP = {
    "VCU/CarState/speed": "vcu_speed",
    "TPU/GPS/GroundSpeed": "gps_ground_speed",
    "TPU/GPS/Location": "gps_location",
    "TPU/GPS/Altitude": "gps_altitude",
    "TPU/GPS/Mode": "gps_mode",
    "TPU/GPS/PPS": "gps_pps",
    "DTI/RPM/ERPM": "motor_erpm",
}
GPS_SENSORS = ["gps_ground_speed", "gps_location", "gps_altitude", "gps_mode"]


class FakePenelope:
    """Pages a frame the way BaseClient.iter_pages does: sorted by key, page_size rows."""

    def __init__(self, df, page_size=100_000):
        self.df = df
        self.page_size = page_size

    def iter_readings(self, run_id, key, data_type_names=None):
        df = self.df
        if data_type_names is not None:
            df = df[df["raw_tag"].isin(list(data_type_names))]
        df = df.sort_values(list(key), ignore_index=True)
        for start in range(0, len(df), self.page_size):
            yield df.iloc[start : start + self.page_size]

    def read_run_readings(self, run_id, data_type_names):
        pages = list(self.iter_readings(run_id, ("time", "raw_tag"), data_type_names))
        if not pages:
            return pd.DataFrame(columns=["time", "raw_tag", "values"])
        return pd.concat(pages, ignore_index=True)


class FakeOrion:
    def __init__(self):
        self.pages = []

    def read_sensor_map(self):
        return dict(SENSOR_MAP)

    def delete_for_run(self, table, run_id):
        self.pages = []

    def append(self, table, df):
        self.pages.append(df)

    def output(self):
        return pd.concat(self.pages, ignore_index=True)


def to_time(epoch_s):
    return pd.to_datetime(np.asarray(epoch_s), unit="s", utc=True)


def penelope_frame(run, vcu=True, with_extras=True):
    """Penelope `data` rows for a synthetic run.

    Location/Altitude/Mode share every GroundSpeed timestamp (same packet). Location's
    value is the TRUE measurement time, so the test can check each corrected row.
    """
    vcu_t, vcu_mph, gps_t, gps_mph, _, measured_t = run
    frames = []
    if vcu:
        frames.append(rows("VCU/CarState/speed", vcu_t, vcu_mph))
    frames.append(rows("TPU/GPS/GroundSpeed", gps_t, gps_mph / MS_TO_MPH))
    frames.append(rows("TPU/GPS/Location", gps_t, T0 + measured_t))
    frames.append(rows("TPU/GPS/Altitude", gps_t, np.full(len(gps_t), 12.0)))
    frames.append(rows("TPU/GPS/Mode", gps_t, np.full(len(gps_t), 3.0)))
    if with_extras:
        rng = np.random.default_rng(99)
        span = (gps_t[0], gps_t[-1])
        frames.append(rows("TPU/GPS/PPS", rng.uniform(*span, 300), np.full(300, -20.0)))
        frames.append(
            rows("DTI/RPM/ERPM", rng.uniform(*span, 2000), rng.uniform(0, 9e3, 2000))
        )
    df = pd.concat(frames, ignore_index=True)
    # Penelope's key is (time, dataTypeName, runId)
    return df.drop_duplicates(["time", "raw_tag"], ignore_index=True)


def rows(tag, t, values):
    return pd.DataFrame(
        {
            "time": to_time(T0 + np.asarray(t)),
            "raw_tag": tag,
            "values": [[float(v)] for v in values],
        }
    )


def make_step(reader, writer):
    return CleanStep(
        reader=cast(PenelopeClient, reader), writer=cast(OrionDBClient, writer)
    )


def run_clean_step(df, page_size=100_000, gps_time_offset_s=3.0):
    writer = FakeOrion()
    step = make_step(FakePenelope(df, page_size), writer)
    step.run(RunContext(run_id=RUN_ID, gps_time_offset_s=gps_time_offset_s))
    return step, writer.output()


def location_errors(out, change_times=(), margin=30.0):
    """|corrected time - true measurement time| for Location rows away from lag changes."""
    loc = out[out["sensor"] == "gps_location"]
    truth = np.array([v[0] for v in loc["values"]])
    err = np.abs(to_epoch_s(loc["time"]) - truth)
    far = np.ones(len(loc), dtype=bool)
    for c in change_times:
        far &= np.abs(truth - (T0 + c)) > margin
    return err[far]


def test_changing_lag_is_corrected(make_run):
    run = make_run(
        11,
        [(0, 1.0), (500, 6.0), (950, 11.0)],
        outages=[(320, 500), (890, 950)],
        duration=1400,
    )
    step, out = run_clean_step(penelope_frame(run))
    err = location_errors(out, change_times=(500, 950))
    assert np.median(err) < 0.25, np.median(err)
    assert np.percentile(err, 95) < 0.6, np.percentile(err, 95)
    found = sorted(round(s.lag_s) for s in step.gps_segments if s.quality == "ok")
    for expected in (1, 6, 11):
        assert expected in found, (expected, found)


def test_paging_does_not_change_output(make_run):
    run = make_run(12, [(0, 2.0), (500, 7.0)], outages=[(380, 500)], duration=1000)
    df = penelope_frame(run)
    _, whole = run_clean_step(df)
    _, paged = run_clean_step(df, page_size=997)
    assert len(paged) == len(whole) == len(df)
    pd.testing.assert_frame_equal(whole, paged)


def test_same_packet_gets_same_shift(make_run):
    run = make_run(13, [(0, 4.0)], duration=600)
    _, out = run_clean_step(penelope_frame(run, with_extras=False))
    times = {
        s: np.sort(out.loc[out["sensor"] == s, "time"].to_numpy()) for s in GPS_SENSORS
    }
    for sensor in GPS_SENSORS[1:]:
        assert np.array_equal(times[sensor], times["gps_ground_speed"]), sensor


def test_pps_and_non_gps_rows_are_untouched(make_run):
    run = make_run(14, [(0, 5.0)], duration=600)
    df = penelope_frame(run)
    _, out = run_clean_step(df)
    for tag, sensor in [
        ("TPU/GPS/PPS", "gps_pps"),
        ("DTI/RPM/ERPM", "motor_erpm"),
        ("VCU/CarState/speed", "vcu_speed"),
    ]:
        before = np.sort(df.loc[df["raw_tag"] == tag, "time"].to_numpy())
        after = np.sort(out.loc[out["sensor"] == sensor, "time"].to_numpy())
        assert np.array_equal(before, after), sensor
    # and the GPS rows did move, by roughly the true lag
    gs_before = np.sort(
        df.loc[df["raw_tag"] == "TPU/GPS/GroundSpeed", "time"].to_numpy()
    )
    gs_after = np.sort(out.loc[out["sensor"] == "gps_ground_speed", "time"].to_numpy())
    shift = np.median((gs_before - gs_after) / np.timedelta64(1, "s"))
    assert abs(shift - 5.0) < 0.25, shift


def test_no_vcu_uses_default_lag(make_run):
    run = make_run(15, [(0, 1.0)], duration=300)
    df = penelope_frame(run, vcu=False)
    step, out = run_clean_step(df, gps_time_offset_s=2.5)
    assert [s.quality for s in step.gps_segments] == ["default"]
    gs_before = np.sort(
        df.loc[df["raw_tag"] == "TPU/GPS/GroundSpeed", "time"].to_numpy()
    )
    gs_after = np.sort(out.loc[out["sensor"] == "gps_ground_speed", "time"].to_numpy())
    assert ((gs_before - gs_after) == np.timedelta64(2500, "ms")).all()


def test_parked_run_uses_default_lag(make_run):
    run = make_run(16, [(0, 1.0)], parked=True, duration=600)
    step, out = run_clean_step(penelope_frame(run))
    assert all(s.quality == "default" for s in step.gps_segments)
    assert all(s.lag_s == 3.0 for s in step.gps_segments)


def test_fallback_segment_lag_is_applied():
    """A segment the tracker couldn't measure carries the nearest good segment's lag;
    transform must apply that lag, not the segment's own raw estimate."""
    t = np.array([10.0, 20.0, 110.0, 120.0, 400.0, 410.0])
    df = rows("TPU/GPS/Location", t, np.zeros(len(t)))
    step = make_step(FakePenelope(df), FakeOrion())
    step.sensor_map = dict(SENSOR_MAP)
    step.gps_segments = [
        Segment(T0 + 0, T0 + 100, 1.0, 0.9, 1.1, 400, 300, "ok"),
        Segment(T0 + 110, T0 + 150, 1.0, np.nan, np.nan, 40, 5, "fallback"),
        Segment(T0 + 400, T0 + 900, 6.0, 5.9, 6.1, 2000, 1500, "ok"),
    ]
    out = step.transform(df, RunContext(run_id=RUN_ID))
    shift = (df["time"] - out["time"]) / pd.Timedelta(seconds=1)
    assert np.allclose(shift, [1.0, 1.0, 1.0, 1.0, 6.0, 6.0])


def test_failed_estimate_keeps_previous_output(make_run):
    """The run's old cleaned_data is only deleted once the lag estimate succeeded."""
    run = make_run(17, [(0, 1.0)], duration=300)
    reader = FakePenelope(penelope_frame(run))
    writer = FakeOrion()
    writer.pages = ["previous output"]

    def broken_read(run_id, data_type_names):
        raise TimeoutError("statement timeout")

    reader.read_run_readings = broken_read
    with pytest.raises(TimeoutError):
        make_step(reader, writer).prepare(RunContext(run_id=RUN_ID))
    assert writer.pages == ["previous output"]


def test_transform_without_segments_raises():
    df = rows("TPU/GPS/Location", [1.0, 2.0], [0.0, 0.0])
    step = make_step(FakePenelope(df), FakeOrion())
    step.sensor_map = dict(SENSOR_MAP)
    with pytest.raises(ValueError, match="no GPS lag segments"):
        step.transform(df, RunContext(run_id=RUN_ID))


def test_lag_is_applied_to_the_microsecond():
    """Lags from the float grid (3.0 -> 2.99999999999997) shift by exactly 3 s."""
    df = rows("TPU/GPS/Location", [1.0, 2.0], [0.0, 0.0])
    step = make_step(FakePenelope(df), FakeOrion())
    step.sensor_map = dict(SENSOR_MAP)
    noisy = float(np.arange(-5.0, 20.025, 0.05)[160])
    assert noisy != 3.0
    step.gps_segments = [Segment(T0, T0 + 2, noisy, np.nan, np.nan, 2, 0, "ok")]
    out = step.transform(df, RunContext(run_id=RUN_ID))
    assert ((df["time"] - out["time"]) == pd.Timedelta(seconds=3)).all()


def test_overlapping_segments_drop_duplicate_rows(caplog):
    """A later segment with a bigger lag can land a row on an earlier row's corrected
    time; the duplicate is dropped (and logged) instead of breaking the primary key."""
    df = rows("TPU/GPS/Location", [10.0, 15.0, 20.0], [1.0, 2.0, 3.0])
    step = make_step(FakePenelope(df), FakeOrion())
    step.sensor_map = dict(SENSOR_MAP)
    step.gps_segments = [
        Segment(T0 + 10, T0 + 15, 1.0, np.nan, np.nan, 2, 0, "ok"),
        Segment(T0 + 20, T0 + 20, 6.0, np.nan, np.nan, 1, 0, "fallback"),
    ]
    out = step.transform(df, RunContext(run_id=RUN_ID))
    # 15 - 1 == 20 - 6: the first row at that corrected time is kept
    assert [v[0] for v in out["values"]] == [1.0, 2.0]
    assert "duplicate (time, sensor)" in caplog.text
