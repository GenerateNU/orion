"""OrionDB SELECT builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from sqlalchemy import Select, select

from orion_core.models.orion import Run, SensorSources


def select_sensor_sources() -> Select:
    """Every Penelope tag we know how to map, and the generic sensor it maps to."""
    return select(
        SensorSources.source_data_type_name.label("raw_tag"),
        SensorSources.sensor,
    )


def select_runs() -> Select:
    """Every run, newest drive first."""
    return select(Run).order_by(Run.start_time.desc(), Run.run_id)


def select_run(run_id: str) -> Select:
    """One run by id."""
    return select(Run).where(Run.run_id == run_id)
