"""Tests for StateConfig loading and validation."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from orion_pipeline.steps.state_estimation.state_config import StateConfig


def test_state_config_loads_real_file():
    """Load the real state_config.toml and verify it parses."""
    config = StateConfig.load("services/pipeline/config/state_config.toml")

    assert config.sigma_jerk == 1.0
    assert config.sigma_alpha == 0.1
    assert config.straight_threshold == 1e-6
    assert len(config.covariance_diag) == 6
    assert "gps_location" in config.sensors
    assert "vcu_speed" in config.sensors


def test_state_config_sensors_have_r_matrices():
    """Verify sensor configs calculate R matrices correctly."""
    config = StateConfig.load("services/pipeline/config/state_config.toml")

    gps_cfg = config.sensors["gps_location"]
    assert gps_cfg.std == [1.5, 1.5]
    assert gps_cfg.gate == 9.21

    # R should be diag([1.5^2, 1.5^2])
    expected_r = np.diag([2.25, 2.25])
    np.testing.assert_array_almost_equal(gps_cfg.R, expected_r)


def test_state_config_p0_property():
    """Verify P0 is calculated from covariance_diag."""
    config = StateConfig.load("services/pipeline/config/state_config.toml")

    expected_p0 = np.diag(config.covariance_diag)
    np.testing.assert_array_equal(config.P0, expected_p0)


def test_state_config_missing_model_key():
    """Fail with clear error when model section missing key."""
    broken_toml = """
[initial_state]
covariance_diag = [2.25, 2.25, 1.0, 0.09, 0.25, 4.0]

[ukf]
alpha = 0.5
beta = 2.0
kappa = 0.0

[sensors.gps_location]
std = [1.5, 1.5]
gate = 9.21

[sensors.vcu_speed]
std = [0.5]
gate = 6.63
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(broken_toml)
        f.flush()

        try:
            with pytest.raises(KeyError, match="model"):
                StateConfig.load(f.name)
        finally:
            Path(f.name).unlink()


def test_state_config_missing_sensor_std():
    """Fail when sensor missing std."""
    broken_toml = """
[model]
straight_threshold = 1e-6
sigma_jerk = 1.0
sigma_alpha = 0.1

[initial_state]
covariance_diag = [2.25, 2.25, 1.0, 0.09, 0.25, 4.0]

[ukf]
alpha = 0.5
beta = 2.0
kappa = 0.0

[sensors.gps_location]
gate = 9.21
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(broken_toml)
        f.flush()

        try:
            with pytest.raises(KeyError, match="std|gate"):
                StateConfig.load(f.name)
        finally:
            Path(f.name).unlink()


def test_state_config_file_not_found():
    """Fail when config file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        StateConfig.load("/nonexistent/path/config.toml")
