"""Raw sensor data, read straight from Penelope so it matches what the car sent."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SensorResponse(BaseModel):
    """One row of Penelope's `data_type` table."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(
        description=(
            "Penelope `dataTypeName`. Use this in `sensors` on "
            "`GET /runs/{run_id}/sensors/data`."
        ),
        examples=["TPU/GPS/Location"],
    )
    unit: str | None = Field(
        description="Unit Penelope records for this sensor. `null` if it has none.",
        examples=["coordinate"],
    )


class SensorSeries(BaseModel):
    """One sensor's readings in columnar form: `values[i]` was recorded at `time[i]`."""

    time: list[datetime] = Field(
        description=(
            "Reading timestamps (UTC), ascending. Lagged sensors (e.g. `TPU/GPS/*`) "
            "are shifted by `GPS_TIME_OFFSET_S`; all others are as stored in Penelope."
        ),
        examples=[["2026-10-01T14:02:11.000Z", "2026-10-01T14:02:12.000Z"]],
    )
    values: list[list[float | None]] = Field(
        description=(
            "Penelope's `values[]` array for each reading, as stored. Same length as "
            "`time`. Array positions aren't named yet, so a multi-value sensor like "
            "`TPU/GPS/Location` returns e.g. `[lat, lon]` as a plain array."
        ),
        examples=[[[42.3398, -71.0892], [42.3399, -71.0890]]],
    )


class SensorDataResponse(BaseModel):
    """Every reading of the requested sensors for one run, between `start` and `end`."""

    run_id: str = Field(description="Penelope run id.", examples=["run-123"])
    start: datetime = Field(description="Inclusive lower time bound, as requested.")
    end: datetime = Field(description="Inclusive upper time bound, as requested.")
    series: dict[str, SensorSeries] = Field(
        default_factory=dict,
        description=(
            "One series per requested sensor, keyed by Penelope `dataTypeName`. A "
            "sensor with no rows in the range comes back with empty `time` / `values` "
            "instead of an error."
        ),
        examples=[
            {
                "TPU/GPS/Location": {
                    "time": ["2026-10-01T14:02:11.000Z"],
                    "values": [[42.3398, -71.0892]],
                }
            }
        ],
    )


class LapSensorSeries(SensorSeries):
    """One sensor's readings during one lap, with how far round the lap each was."""

    lap_percent: list[float] = Field(
        description=(
            "How far round the run's ideal lap the car was at each reading, 0-100: the "
            "`lap_percent` of the estimated position nearest in time. Same length as "
            "`time`."
        ),
        examples=[[41.7, 41.9]],
    )


class LapSensorDataResponse(BaseModel):
    """Every reading of the requested sensors while one lap was in a percent range."""

    run_id: str = Field(description="Penelope run id.", examples=["run-123"])
    lap_id: int = Field(description="The lap these readings are from.", examples=[3])
    start: datetime | None = Field(
        description=(
            "First time the lap was in the percent range. `null` if it never was."
        ),
    )
    end: datetime | None = Field(
        description="Last time the lap was in the percent range. `null` if it never was.",
    )
    series: dict[str, LapSensorSeries] = Field(
        default_factory=dict,
        description=(
            "One series per requested sensor, keyed by Penelope `dataTypeName`, each "
            "with the `lap_percent` of every reading. A lap that was never in the "
            "percent range comes back with empty series."
        ),
    )
