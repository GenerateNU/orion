from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.clean_step.clean_step import CleanStep

START = datetime(2026, 1, 1, 12, 0, 0)


def raw_page(*offsets_s: float, raw_tag: str = "speed_raw") -> pd.DataFrame:
    """Penelope rows for one tag at `START + offset` seconds."""
    return pd.DataFrame(
        {
            "time": [START + timedelta(seconds=s) for s in offsets_s],
            "raw_tag": raw_tag,
            "values": [1.0] * len(offsets_s),
        }
    )


def run_clean_step(pages: list[pd.DataFrame]) -> MagicMock:
    """Run CleanStep over `pages` without a database, and return its mock writer."""
    reader = MagicMock()
    reader.iter_readings.return_value = iter(pages)
    writer = MagicMock()
    writer.read_sensor_map.return_value = {"speed_raw": "speed"}
    CleanStep(reader=reader, writer=writer).run(
        RunContext(run_id="run-1", gps_time_offset_s=0)
    )
    return writer


def test_sets_run_bounds_across_pages():
    writer = run_clean_step([raw_page(0, 5), raw_page(10, 42)])
    writer.set_run_bounds.assert_called_once_with(
        "run-1", START, START + timedelta(seconds=42)
    )


def test_no_readings_clears_run_bounds():
    writer = run_clean_step([])
    writer.set_run_bounds.assert_called_once_with("run-1", None, None)
