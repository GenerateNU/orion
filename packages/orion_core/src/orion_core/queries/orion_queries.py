"""OrionDB SELECT builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from typing import Any

from sqlalchemy import Select, select

from orion_core.models.orion import SensorSources


def select_sensor_sources() -> Select[*tuple[Any, ...]]:
    """Every Penelope tag we know how to map, and the generic sensor it maps to."""
    return select(
        SensorSources.source_data_type_name.label("raw_tag"),
        SensorSources.sensor,
    )
