from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from models.vehicle import StateEstimate, vehicle_states


def _minimal_states(n: int = 1, **overrides) -> pd.DataFrame:
    """Build a valid states frame with only the required columns, unless overridden."""
    start = datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC)
    cols = {
        "timestamp": pd.date_range(start, periods=n, freq="100ms"),
        "speed_mps": [27.3] * n,
        "latitude": [42.36] * n,
        "longitude": [-71.06] * n,
    }
    cols.update(overrides)
    return pd.DataFrame(cols)


def test_vehicle_states_constructs_with_only_required_columns():
    """timestamp, speed_mps, latitude, longitude are the required set."""
    df = vehicle_states(_minimal_states())
    assert df["speed_mps"].iloc[0] == 27.3
    assert df["latitude"].iloc[0] == 42.36


def test_vehicle_states_optional_columns_default_to_missing():
    """Columns we don't have values for yet (heading, yaw rate, altitude) must default, not be silently required."""
    df = vehicle_states(_minimal_states())
    assert df["heading_deg"].isna().all()
    assert df["yaw_rate_dps"].isna().all()
    # not every sensor setup reports altitude
    assert df["altitude"].isna().all()


def test_vehicle_states_missing_required_column_raises():
    """location is required -- omitting it must fail loudly."""
    with pytest.raises(ValueError, match="latitude"):
        vehicle_states(pd.DataFrame({
            "timestamp": [datetime(2026, 9, 19, 12, 0, 0, tzinfo=UTC)],
            "speed_mps": [27.3],
            "longitude": [-71.06],
        }))  # no latitude


def test_state_estimate_defaults_to_forward_pass():
    """Forward-pass output: no covariance required, is_smoothed False."""
    est = StateEstimate(states=_minimal_states())
    assert est.covariance is None
    assert est.is_smoothed is False


def test_state_estimate_accepts_covariance_and_smoothed_flag():
    """After URTS, an estimate carries one covariance matrix per state row and is_smoothed=True."""
    cov = np.tile(np.eye(2) * 0.5, (3, 1, 1))
    est = StateEstimate(states=_minimal_states(3), covariance=cov, is_smoothed=True)
    assert est.is_smoothed is True
    assert est.covariance.shape == (3, 2, 2)
    np.testing.assert_array_equal(est.covariance[0], [[0.5, 0.0], [0.0, 0.5]])


def test_state_estimate_validates_states():
    """A StateEstimate can't be built around a broken states frame."""
    with pytest.raises(ValueError, match="latitude"):
        StateEstimate(states=_minimal_states().drop(columns=["latitude"]))


@pytest.mark.parametrize("shape", [(2, 2, 2), (3, 2, 3), (3, 4)])
def test_state_estimate_rejects_misshapen_covariance(shape):
    """Covariance must be (len(states), n, n) -- one square matrix per row."""
    with pytest.raises(ValueError, match="covariance"):
        StateEstimate(states=_minimal_states(3), covariance=np.zeros(shape))
