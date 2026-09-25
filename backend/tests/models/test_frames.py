from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from backend.models.frames import validate_frame

SCHEMA = {"id": "string", "timestamp": "datetime64[ns, UTC]", "value": "float64", "note": "string"}
REQUIRED = {"id", "timestamp", "value"}


def _frame(**overrides) -> pd.DataFrame:
    cols = dict(id=["a", "b"], timestamp=[datetime(2026, 9, 19, 12, 0, 0)] * 2, value=[1.0, 2.0])
    cols.update(overrides)
    return pd.DataFrame(cols)


def test_casts_to_schema_dtypes():
    df = validate_frame(_frame(value=[1, 2]), SCHEMA, REQUIRED)
    assert df.dtypes.astype(str).to_dict() == {
        "id": "string", "timestamp": "datetime64[ns, UTC]", "value": "float64", "note": "string",
    }


def test_drops_extra_columns():
    df = validate_frame(_frame(junk=[1, 2]), SCHEMA, REQUIRED)
    assert list(df.columns) == list(SCHEMA)


def test_does_not_mutate_input():
    original = _frame()
    validate_frame(original, SCHEMA, REQUIRED)
    assert list(original.columns) == ["id", "timestamp", "value"]


def test_converts_tz_aware_timestamps_to_utc():
    est = timezone(timedelta(hours=-5))
    df = validate_frame(_frame(timestamp=[datetime(2026, 9, 19, 7, 0, 0, tzinfo=est)] * 2), SCHEMA, REQUIRED)
    assert df["timestamp"].iloc[0] == pd.Timestamp("2026-09-19 12:00:00", tz="UTC")


def test_rejects_null_in_required_column():
    """A required column that's present but has a hole must fail, same as Pydantic rejecting None."""
    with pytest.raises(ValueError, match="null value.*value"):
        validate_frame(_frame(value=[1.0, None]), SCHEMA, REQUIRED)


def test_allows_null_in_optional_column():
    df = validate_frame(_frame(note=["hi", None]), SCHEMA, REQUIRED)
    assert pd.isna(df["note"].iloc[1])


def test_rejects_uncastable_value():
    with pytest.raises(ValueError):
        validate_frame(_frame(value=["abc", "1.0"]), SCHEMA, REQUIRED)


def test_rejects_unparseable_timestamp():
    with pytest.raises(ValueError):
        validate_frame(_frame(timestamp=["not a date", "2026-09-19"]), SCHEMA, REQUIRED)


def test_empty_frame_is_valid():
    """An empty batch (e.g. a Penelope query with no rows) should pass through, not error."""
    df = validate_frame(pd.DataFrame({"id": [], "timestamp": [], "value": []}), SCHEMA, REQUIRED)
    assert len(df) == 0
    assert list(df.columns) == list(SCHEMA)
