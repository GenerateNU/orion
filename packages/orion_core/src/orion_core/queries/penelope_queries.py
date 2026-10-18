"""Penelope SELECT builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select

from orion_core.models.penelope import data_table, data_type_table


def select_readings(
    run_id: str,
    limit: int | None = None,
    data_type_names: Collection[str] | None = None,
) -> Select[*tuple[Any, ...]]:
    """`data_type_names`, if given, keeps only rows with those raw tags."""
    stmt = (
        select(
            data_table.c.time,
            data_table.c.dataTypeName.label("raw_tag"),
            data_table.c["values"],
        )
        .where(data_table.c.runId == run_id)
        .order_by(data_table.c.time)
    )
    if data_type_names is not None:
        stmt = stmt.where(data_table.c.dataTypeName.in_(list(data_type_names)))
    return stmt.limit(limit) if limit else stmt


def select_readings_between(
    run_id: str,
    data_type_names: Collection[str],
    start: datetime,
    end: datetime,
) -> Select:
    """Readings for the given raw tags with `start <= time <= end`.

    Unlike `select_readings`, every filter is required, so an API caller can't
    accidentally pull a whole run.
    """
    return select_readings(run_id, data_type_names=data_type_names).where(
        data_table.c.time >= start, data_table.c.time <= end
    )


def select_data_types() -> Select:
    """Penelope's sensor types, by name."""
    return select(data_type_table.c.name, data_type_table.c.unit).order_by(
        data_type_table.c.name
    )
