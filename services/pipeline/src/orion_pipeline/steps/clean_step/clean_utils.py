from collections.abc import Collection

import pandas as pd


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


def shift_sensor_time(
    df: pd.DataFrame, sensors: Collection[str], offset_s: float
) -> pd.DataFrame:
    """Add `offset_s` seconds to `time` for rows of `sensors` (e.g. GPS lag correction)."""
    if not offset_s:
        return df
    df = df.copy()
    mask = df["sensor"].isin(list(sensors))
    df.loc[mask, "time"] = df.loc[mask, "time"] + pd.Timedelta(seconds=offset_s)
    return df
