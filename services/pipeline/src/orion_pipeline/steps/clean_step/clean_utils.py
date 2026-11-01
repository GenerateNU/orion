from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import pandas as pd

from orion_pipeline.steps.clean_step.gps_lag import Segment, lag_at


def map_sensor_names(
    df: pd.DataFrame, sensor_map: dict[str, str], run_id: str
) -> pd.DataFrame:
    """Rename raw Penelope tags to generic sensor names, shaped like `cleaned_data`.

    Extract already filters to mapped tags, so an unmapped tag here is a bug.
    """
    sensor = df["raw_tag"].map(sensor_map)
    if sensor.isna().any():
        unmapped = sorted(df.loc[sensor.isna(), "raw_tag"].unique())
        raise ValueError(f"unmapped raw tags reached transform: {unmapped}")
    return pd.DataFrame(
        {
            "run_id": run_id,
            "time": df["time"],
            "sensor": sensor,
            "values": df["values"],
        }
    )


def to_epoch_s(times: pd.Series) -> npt.NDArray[np.float64]:
    """Datetimes (tz-aware or naive) as float seconds since the epoch."""
    if times.empty:
        return np.empty(0)
    epoch = pd.Timestamp(0, tz=times.dt.tz)
    return np.asarray((times - epoch) / pd.Timedelta(seconds=1), dtype=np.float64)


def first_values(values: pd.Series) -> npt.NDArray[np.float64]:
    """First element of each `values` array, NaN where the array is empty or missing."""
    return np.array(
        [v[0] if v is not None and len(v) else np.nan for v in values], dtype=float
    )


def correct_gps_time(
    df: pd.DataFrame,
    shifted: pd.Series,
    segments: Sequence[Segment],
) -> pd.DataFrame:
    """Subtract the tracked GPS lag from `time` for the rows where `shifted` is True.

    The lag comes from the run's segment table (`gps_lag.lag_at`), so it
    depends only on each row's own timestamp and never on which page the row is in.
    GPS rows with no segments (the lag was never estimated) are a bug and raise.
    """
    if not shifted.any():
        return df
    if not segments:
        raise ValueError(
            "no GPS lag segments; estimate the run's lag before correcting"
        )
    df = df.copy()
    lag = lag_at(to_epoch_s(df.loc[shifted, "time"]), segments)
    # The lag grid carries float noise (3.0 -> 2.99999999999997); round to the
    # microsecond, the timestamp resolution, so a 3 s lag shifts by exactly 3 s.
    lag = np.round(lag, 6)
    df.loc[shifted, "time"] = df.loc[shifted, "time"] - pd.to_timedelta(lag, unit="s")
    return df
