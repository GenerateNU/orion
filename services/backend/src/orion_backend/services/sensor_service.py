from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.exceptions import InvalidParameterError
from orion_backend.repositories.lap_repository import LapRepository
from orion_backend.repositories.sensor_repository import SensorRepository
from orion_backend.schemas.sensor_schema import (
    SensorDataResponse,
    SensorResponse,
    SensorSeries,
)
from orion_core.db.sensor_catalog import lagged_raw_tags
from orion_core.settings import get_settings


class SensorService:
    def __init__(self, penelope_db: AsyncSession, orion_db: AsyncSession):
        self.repository = SensorRepository(penelope_db)
        self.laps = LapRepository(orion_db)
        settings = get_settings()
        self.offset = timedelta(seconds=settings.gps_time_offset_s)
        self.tolerance = timedelta(seconds=settings.lap_percent_match_tolerance_s)
        self.lagged = lagged_raw_tags()

    async def list_sensors(self) -> list[SensorResponse]:
        rows = await self.repository.list_data_types()
        return [SensorResponse.model_validate(row) for row in rows]

    async def get_sensor_data(
        self,
        run_id: str,
        sensors: list[str],
        start: datetime,
        end: datetime,
        gps_offset_on: bool = True,
        with_lap_percent: bool = False,
    ) -> SensorDataResponse:
        """Every reading of `sensors` in `[start, end]`, one series per sensor.

        With `gps_offset_on`, `gps_time_offset_s` is added to the times of lagged
        sensors (see `sensor_catalog`), and the window applies to the shifted times.
        With `with_lap_percent`, each series also gets `lap_id` and `lap_percent`
        (see `attach_lap_progress`), matched on those shifted times. A sensor with no
        rows in the range (or an unknown run) comes back empty.
        """
        sensors = list(dict.fromkeys(sensors))
        if not sensors:
            raise InvalidParameterError("`sensors` must name at least one sensor")
        if start > end:
            raise InvalidParameterError("`start` must be at or before `end`")

        lagged = self.lagged if gps_offset_on else frozenset()

        series = {name: SensorSeries(time=[], values=[]) for name in sensors}
        rows = await self.repository.list_readings(
            run_id, sensors, start, end, lagged, self.offset
        )
        for row in rows:
            reading = row._mapping
            time = reading["time"]
            if reading["raw_tag"] in lagged:
                time += self.offset
            series[reading["raw_tag"]].time.append(time)
            series[reading["raw_tag"]].values.append(reading["values"])

        if with_lap_percent:
            # Positions just outside the window can still be a reading's nearest.
            positions = await self.laps.list_lap_percents(
                run_id, to_utc(start) - self.tolerance, to_utc(end) + self.tolerance
            )
            laps = await self.laps.list_laps(run_id)
            position_frame = pd.DataFrame(positions, columns=["time", "lap_percent"])
            lap_frame = pd.DataFrame(laps, columns=["lap_id", "start_time", "end_time"])
            for one in series.values():
                one.lap_id, one.lap_percent = attach_lap_progress(
                    one.time, position_frame, lap_frame, self.tolerance
                )

        return SensorDataResponse(run_id=run_id, start=start, end=end, series=series)


def to_utc(time: datetime) -> datetime:
    """`time` as a naive UTC datetime, like OrionDB stores it. Naive input is
    taken to be UTC already."""
    return time if time.tzinfo is None else time.astimezone(UTC).replace(tzinfo=None)


def attach_lap_progress(
    times: list[datetime],
    positions: pd.DataFrame,
    laps: pd.DataFrame,
    tolerance: timedelta,
) -> tuple[list[int | None], list[float | None]]:
    """Each reading's lap and lap percentage.

    Args:
        times: The readings' times, in any order, naive UTC or timezone-aware.
        positions: The run's estimated positions near the readings: `time` (naive
            UTC) and `lap_percent` (None where the step gave the point none).
        laps: The run's `laps` rows: `lap_id`, `start_time`, `end_time`.
        tolerance: How far a reading may be from its nearest position.

    Returns:
        `(lap_id, lap_percent)`, one entry per reading. `lap_id` comes from the lap
        whose `[start_time, end_time)` holds the reading, with the last lap's end
        included. `lap_percent` is the nearest position's, if one is within
        `tolerance`. Either is None when there's no match.
    """
    if not times:
        return [], []
    at = pd.Series(pd.to_datetime([to_utc(t) for t in times])).astype("datetime64[ns]")
    return _lap_ids(at, laps), _lap_percents(at, positions, tolerance)


def _lap_ids(at: pd.Series, laps: pd.DataFrame) -> list[int | None]:
    if laps.empty:
        return [None] * len(at)
    starts = laps["start_time"].astype("datetime64[ns]").to_numpy()
    ends = laps["end_time"].astype("datetime64[ns]").to_numpy()
    t = at.to_numpy()
    index = np.searchsorted(starts, t, side="right") - 1
    clipped = np.clip(index, 0, len(starts) - 1)
    last = clipped == len(starts) - 1
    inside = (index >= 0) & ((t < ends[clipped]) | (last & (t == ends[clipped])))
    ids = laps["lap_id"].to_numpy()
    return [int(ids[i]) if ok else None for i, ok in zip(clipped, inside, strict=True)]


def _lap_percents(
    at: pd.Series, positions: pd.DataFrame, tolerance: timedelta
) -> list[float | None]:
    if positions.empty:
        return [None] * len(at)
    readings = pd.DataFrame({"time": at, "order": range(len(at))}).sort_values("time")
    nearest = pd.merge_asof(
        readings,
        positions.astype({"time": "datetime64[ns]", "lap_percent": "float64"}),
        on="time",
        direction="nearest",
        tolerance=pd.Timedelta(tolerance),
    ).sort_values("order")
    return [None if pd.isna(p) else float(p) for p in nearest["lap_percent"]]
