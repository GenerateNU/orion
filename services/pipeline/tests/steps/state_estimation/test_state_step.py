from unittest.mock import Mock

import numpy as np
import pandas as pd

from orion_core.models.orion import UkfState
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.state_estimation.state_step import StateStep
from orion_pipeline.steps.state_estimation.ukf_step import Tick

T0 = pd.Timestamp("2026-01-01")


def tick(ms: int, started: bool = False) -> Tick:
    """A tick ms after T0. On a startup tick the prediction fields are None."""
    x, p = np.arange(6.0), np.eye(6)
    pred = (None, None, None) if started else (x, p, 2 * p)
    return Tick(T0 + pd.Timedelta(milliseconds=ms), x, p, *pred)


def test_transform_makes_ukf_states_rows():
    # extract adds the origin columns
    ticks = pd.DataFrame([tick(0, started=True), tick(10)]).assign(
        origin_lat=42.0, origin_lon=-71.0
    )

    rows = StateStep(Mock(), Mock()).transform(ticks, RunContext(run_id="run"))

    assert set(rows.columns) == {c.name for c in UkfState.__table__.columns}
    assert list(rows["run_id"]) == ["run", "run"]
    assert list(rows["origin_lat"]) == [42.0, 42.0]
    start, step = rows.iloc[0], rows.iloc[1]
    assert start["x"] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert start["p"] == np.eye(6).ravel().tolist()
    assert start["x_pred"] is None and start["cross_cov"] is None
    assert step["cross_cov"] == (2 * np.eye(6)).ravel().tolist()
