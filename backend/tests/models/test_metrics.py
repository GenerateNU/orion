from datetime import UTC, datetime
 
import pytest
from pydantic import ValidationError
 
from models.metrics import AnalysisResult
 
 
def test_analysis_result_constructs_with_required_fields():
    result = AnalysisResult(
        window_start=datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC),
        window_end=datetime(2026, 9, 19, 12, 1, 30, tzinfo=UTC),
        avg_speed_mps=25.0,
        max_speed_mps=41.2,
        total_distance_m=2250.0,
    )
    assert result.avg_speed_mps == 25.0
    # optional fields not tied to a specific lap/battery reading must default
    assert result.lap_number is None
    assert result.battery_drain_rate_v_per_min is None
 
 
def test_analysis_result_missing_required_field_raises():
    """total_distance_m is required -- a result without it shouldn't validate."""
    with pytest.raises(ValidationError):
        AnalysisResult(
            window_start=datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC),
            window_end=datetime(2026, 9, 19, 12, 1, 30, tzinfo=UTC),
            avg_speed_mps=25.0,
            max_speed_mps=41.2,
        )  # no total_distance_m
 
 
def test_analysis_result_accepts_lap_specific_fields():
    """Confirms lap_number and battery_drain_rate_v_per_min can be set, not just omitted."""
    result = AnalysisResult(
        window_start=datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC),
        window_end=datetime(2026, 9, 19, 12, 1, 30, tzinfo=UTC),
        avg_speed_mps=25.0,
        max_speed_mps=41.2,
        total_distance_m=2250.0,
        lap_number=3,
        battery_drain_rate_v_per_min=0.02,
    )
    assert result.lap_number == 3
    assert result.battery_drain_rate_v_per_min == 0.02