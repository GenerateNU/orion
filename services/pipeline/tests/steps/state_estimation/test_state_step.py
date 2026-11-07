from unittest.mock import Mock

import numpy as np
import pandas as pd

from orion_core.models.orion import EstimatedCarState
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.state_estimation.state_step import StateStep
from orion_pipeline.steps.state_estimation.ukf_step import Tick

T0 = pd.Timestamp("2026-01-01")


def tick(ms: int, started: bool = False) -> Tick:
    """A tick ms after T0. On a startup tick the prediction fields are None."""
    x, p = np.arange(6.0), np.eye(6)
    pred = (None, None, None) if started else (x, p, 2 * p)
    return Tick(T0 + pd.Timedelta(milliseconds=ms), x, p, *pred)


def test_transform_makes_estimated_car_state_rows():
    # extract adds the origin columns
    ticks = pd.DataFrame([tick(0, started=True), tick(10)]).assign(
        origin_lat=42.0, origin_lon=-71.0
    )

    rows = StateStep(Mock(), Mock()).transform(ticks, RunContext(run_id="run"))

    assert set(rows.columns) == {c.name for c in EstimatedCarState.__table__.columns}
    assert list(rows["run_id"]) == ["run", "run"]
    # state x = [0, 1, ...]: 0 m east, 1 m north of the origin
    assert rows["longitude"].tolist() == [-71.0, -71.0]
    assert np.allclose(rows["lattitude"], 42.0 + 1 / 111_320.0)


def test_transform_writes_smoothed_positions():
    # Tick 0 is at the origin; tick 1 sits 2 m north of where tick 0 predicted.
    # Gain = cross_cov @ inv(p_pred) = 0.5 I, so smoothing pulls tick 0 halfway
    # along that residual: 1 m north. The last tick is unchanged.
    zero, north_2m = np.zeros(6), np.array([0.0, 2.0, 0, 0, 0, 0])
    p = np.eye(6)
    ticks = pd.DataFrame(
        [
            Tick(T0, zero, p, None, None, None),
            Tick(T0 + pd.Timedelta(milliseconds=10), north_2m, p, zero, 2 * p, p),
        ]
    ).assign(origin_lat=42.0, origin_lon=-71.0)

    rows = StateStep(Mock(), Mock()).transform(ticks, RunContext(run_id="run"))

    assert list(rows["time"]) == list(ticks["time"])
    assert np.allclose(rows["lattitude"], [42.0 + 1 / 111_320.0, 42.0 + 2 / 111_320.0])
    assert np.allclose(rows["longitude"], -71.0)
