from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from orion_backend.derived_metrics.alignment import align_inputs
from orion_backend.derived_metrics.base_metric import DerivedMetric
from orion_backend.derived_metrics.interpolation import Interp, interp_for
from orion_backend.derived_metrics.metric_registry import register_metric
from orion_backend.schemas.sensor_schema import SensorSeries

# Real Penelope topics, so `interp_for` picks the kind under test.
CURRENT = "DTI/Power/DC_Current"  # linear
VOLTAGE = "DTI/Power/Input_Voltage"  # linear
STATE = "VCU/CarState/functional_state"  # previous
FAULT = "BMS/Faults/Critical/Pack_too_hot"  # previous
LOCATION = "TPU/GPS/Location"  # linear, [lat, lon]

T0 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)


def ms(*offsets: float) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([T0 + timedelta(milliseconds=o) for o in offsets])


def frame(times: pd.DatetimeIndex, *columns: list[float]) -> pd.DataFrame:
    return pd.DataFrame(dict(enumerate(columns)), index=times)


def test_topic_kinds_used_by_these_tests():
    assert interp_for(CURRENT) is Interp.LINEAR
    assert interp_for(VOLTAGE) is Interp.LINEAR
    assert interp_for(LOCATION) is Interp.LINEAR
    assert interp_for(STATE) is Interp.PREVIOUS
    assert interp_for(FAULT) is Interp.PREVIOUS
    assert interp_for("VCU/CarState/speed") is Interp.LINEAR


def test_offset_sensors_interpolate_the_non_base_input_at_base_times():
    # Both 4 Hz, voltage 125 ms behind current; tie -> first input is the base.
    current = frame(ms(0, 250, 500, 750), [0.0, 10.0, 20.0, 30.0])
    voltage = frame(ms(125, 375, 625, 875), [100.0, 200.0, 300.0, 400.0])

    aligned = align_inputs({CURRENT: current, VOLTAGE: voltage})

    # Row 0 is before voltage's first sample, so it's outside the overlap.
    assert list(aligned.index) == list(ms(250, 500, 750))
    assert aligned[CURRENT][0].tolist() == [10.0, 20.0, 30.0]
    assert aligned[VOLTAGE][0].tolist() == [150.0, 250.0, 350.0]


def test_most_sampled_input_is_the_default_base():
    current = frame(ms(0, 1000), [0.0, 10.0])
    voltage = frame(ms(0, 250, 500, 750, 1000), [1.0, 2.0, 3.0, 4.0, 5.0])

    aligned = align_inputs({CURRENT: current, VOLTAGE: voltage})

    assert list(aligned.index) == list(ms(0, 250, 500, 750, 1000))
    assert aligned[CURRENT][0].tolist() == [0.0, 2.5, 5.0, 7.5, 10.0]


def test_explicit_base_drives_the_rows():
    current = frame(ms(0, 1000), [0.0, 10.0])
    voltage = frame(ms(0, 250, 500, 750, 1000), [1.0, 2.0, 3.0, 4.0, 5.0])

    aligned = align_inputs({CURRENT: current, VOLTAGE: voltage}, base=CURRENT)

    assert list(aligned.index) == list(ms(0, 1000))
    assert aligned[VOLTAGE][0].tolist() == [1.0, 5.0]


def test_unknown_base_is_rejected():
    with pytest.raises(ValueError, match="base"):
        align_inputs({CURRENT: frame(ms(0), [1.0])}, base=VOLTAGE)


def test_gap_factor_below_one_is_rejected():
    # Below 1, normal sample spacing would count as a dropout.
    with pytest.raises(ValueError, match="gap_factor"):
        align_inputs({CURRENT: frame(ms(0), [1.0])}, gap_factor=0.5)


def test_linear_input_is_nan_across_a_dropout():
    # 100 ms spacing, then a 600 ms hole (> 3x the median spacing).
    current = frame(ms(0, 100, 200, 800, 900, 1000), [0, 1, 2, 8, 9, 10])
    voltage = frame(ms(*range(0, 1001, 100)), [1.0] * 11)

    aligned = align_inputs({CURRENT: current, VOLTAGE: voltage}, base=VOLTAGE)
    filled = aligned[CURRENT][0]

    assert filled[ms(0, 100, 200, 800, 900, 1000)].tolist() == [0, 1, 2, 8, 9, 10]
    assert filled[ms(300, 400, 500, 600, 700)].isna().all()


def test_previous_input_holds_its_value_and_never_interpolates():
    current = frame(ms(0, 100, 200, 300, 400, 500), [1.0] * 6)
    state = frame(ms(0, 250, 500), [2.0, 3.0, 3.0])

    aligned = align_inputs({CURRENT: current, STATE: state})

    filled = aligned[STATE][0][ms(0, 100, 200, 250, 300, 400, 500)]
    assert filled.tolist() == [2.0] * 3 + [3.0] * 4


def test_previous_input_is_nan_across_a_dropout():
    # A periodic state heartbeat at 100 ms, then a 600 ms hole: the logger
    # lost it, so the state there is unknown rather than still 2.
    current = frame(ms(*range(0, 1001, 100)), [1.0] * 11)
    state = frame(ms(0, 100, 200, 800, 900, 1000), [2.0] * 6)

    aligned = align_inputs({CURRENT: current, STATE: state})
    filled = aligned[STATE][0]

    assert (filled[ms(0, 100, 200, 800, 900, 1000)] == 2.0).all()
    assert filled[ms(300, 400, 500, 600, 700)].isna().all()


def test_short_fault_between_base_samples_survives_with_exact_times():
    # Base at 4 Hz; fault on at 130 ms, off at 200 ms, both between samples.
    current = frame(ms(0, 250, 500), [0.0, 25.0, 50.0])
    fault = frame(ms(0, 130, 200, 400, 500), [0.0, 1.0, 0.0, 0.0, 0.0])

    aligned = align_inputs({CURRENT: current, FAULT: fault})

    assert list(aligned.index) == list(ms(0, 130, 200, 250, 500))
    assert aligned[FAULT][0].tolist() == [0.0, 1.0, 0.0, 0.0, 0.0]
    # The base is interpolated at the fault's change times.
    assert aligned[CURRENT][0].tolist() == [0.0, 13.0, 20.0, 25.0, 50.0]


def test_repeated_previous_values_add_no_rows_and_dont_become_the_base():
    # The fault has more samples, but the linear input is still the base.
    current = frame(ms(0, 250, 500), [0.0, 25.0, 50.0])
    fault = frame(ms(*range(0, 501, 50)), [0.0] * 11)

    aligned = align_inputs({CURRENT: current, FAULT: fault})

    assert list(aligned.index) == list(ms(0, 250, 500))


def test_repeated_missing_previous_values_add_no_rows():
    # Consecutive nulls are unchanged; only the switches to and from a value
    # at 100 and 300 ms are changes.
    current = frame(ms(0, 250, 500), [0.0, 25.0, 50.0])
    fault = frame(
        ms(*range(0, 501, 50)),
        [0.0, 0.0, np.nan, np.nan, np.nan, np.nan, 1.0, 1.0, 1.0, 1.0, 1.0],
    )

    aligned = align_inputs({CURRENT: current, FAULT: fault})

    assert list(aligned.index) == list(ms(0, 100, 250, 300, 500))


def test_rows_stop_at_the_earliest_last_sample():
    current = frame(ms(0, 100, 200, 300), [0.0, 1.0, 2.0, 3.0])
    state = frame(ms(0, 100, 200), [1.0, 1.0, 1.0])

    aligned = align_inputs({CURRENT: current, STATE: state})

    assert list(aligned.index) == list(ms(0, 100, 200))


def test_duplicate_timestamps_average_linear_and_keep_last_previous():
    current = frame(ms(0, 0, 100), [1.0, 3.0, 5.0])
    state = frame(ms(0, 0, 100), [1.0, 2.0, 2.0])

    aligned = align_inputs({CURRENT: current, STATE: state})

    assert aligned[CURRENT][0].tolist() == [2.0, 5.0]
    assert aligned[STATE][0].tolist() == [2.0, 2.0]


def test_unsorted_input_is_sorted():
    current = frame(ms(200, 0, 100), [2.0, 0.0, 1.0])

    aligned = align_inputs({CURRENT: current})

    assert aligned[CURRENT][0].tolist() == [0.0, 1.0, 2.0]


def test_missing_values_are_skipped_and_interpolated_over():
    current = frame(ms(0, 100, 200), [0.0, np.nan, 2.0])

    aligned = align_inputs({CURRENT: current})

    assert aligned[CURRENT][0].tolist() == [0.0, 1.0, 2.0]


def test_multi_value_topic_keeps_one_column_per_position():
    location = frame(ms(0, 200), [42.0, 42.2], [-71.0, -71.2])
    current = frame(ms(0, 100, 200), [0.0, 1.0, 2.0])

    aligned = align_inputs({LOCATION: location, CURRENT: current})

    assert list(aligned[LOCATION].columns) == [0, 1]
    assert aligned[LOCATION].loc[ms(100)[0]].tolist() == pytest.approx([42.1, -71.1])


def test_empty_input_gives_an_empty_result():
    current = frame(ms(0, 100), [0.0, 1.0])
    empty = pd.DataFrame([], index=[], dtype=float)

    assert align_inputs({CURRENT: current, VOLTAGE: empty}).empty


def test_non_overlapping_inputs_give_an_empty_result():
    current = frame(ms(0, 100), [0.0, 1.0])
    voltage = frame(ms(500, 600), [1.0, 2.0])

    assert align_inputs({CURRENT: current, VOLTAGE: voltage}).empty


class Power(DerivedMetric):
    name = "test/aligned_power"
    unit = "W"
    inputs = (CURRENT, VOLTAGE)

    def compute(self, aligned: pd.DataFrame) -> pd.Series:
        return aligned[(CURRENT, 0)] * aligned[(VOLTAGE, 0)]


def test_run_uses_default_alignment_end_to_end():
    t = [T0 + timedelta(milliseconds=o) for o in (0, 250, 500)]
    inputs = {
        CURRENT: SensorSeries(time=t, values=[[1.0], [2.0], [3.0]]),
        VOLTAGE: SensorSeries(time=[t[0], t[2]], values=[[100.0], [300.0]]),
    }

    assert Power().run(inputs) == SensorSeries(
        time=t, values=[[100.0], [400.0], [900.0]]
    )


def test_run_with_an_empty_input_returns_an_empty_series():
    inputs = {
        CURRENT: SensorSeries(time=[T0], values=[[1.0]]),
        VOLTAGE: SensorSeries(time=[], values=[]),
    }

    assert Power().run(inputs) == SensorSeries(time=[], values=[])


def test_register_metric_rejects_a_base_that_is_not_an_input():
    class BadBase(Power):
        name = "test/bad_base"
        base = STATE

    with pytest.raises(ValueError, match="test/bad_base"):
        register_metric(BadBase)


def test_register_metric_rejects_a_gap_factor_below_one():
    class BadGap(Power):
        name = "test/bad_gap"
        gap_factor = 0

    with pytest.raises(ValueError, match="gap_factor"):
        register_metric(BadGap)
