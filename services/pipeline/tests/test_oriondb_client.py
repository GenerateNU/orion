from datetime import datetime

import numpy as np
import pandas as pd

from orion_pipeline.clients.oriondb_client import _rows


def test_rows_turn_nan_into_none():
    # A NaN would be written to Postgres as the float NaN; None is written as NULL.
    time = datetime(2026, 1, 1, 12, 0, 0)
    df = pd.DataFrame({"time": [time, time], "lap_percent": [12.5, np.nan]})

    rows = list(_rows(df))

    assert rows == [(time, 12.5), (time, None)]
    assert type(rows[0][1]) is float
