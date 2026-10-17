"""OrionDB SELECT builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from datetime import datetime

from sqlalchemy import Select, select

from orion_core.models.orion import EstimatedCarState, SensorSources


def select_sensor_sources() -> Select:
    """Every Penelope tag we know how to map, and the generic sensor it maps to."""
    return select(
        SensorSources.source_data_type_name.label("raw_tag"),
        SensorSources.sensor,
    )


def select_estimated_positions_between(run_id: str, start: datetime, end: datetime) -> Select:
    """Estimated (lat, lon) for one run in [start, end], ordered by time."""
    return (
        select(
            EstimatedCarState.time,
            EstimatedCarState.lattitude,
            EstimatedCarState.longitude,
        )
        .where(
            EstimatedCarState.run_id == run_id,
            EstimatedCarState.time.between(start, end),
        )
        .order_by(EstimatedCarState.time)
    )
