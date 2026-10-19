"""Penelope SELECT builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select

from orion_core.models.penelope import data_table, data_type_table, run_table


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
) -> Select[*tuple[Any, ...]]:
    """Readings for the given raw tags with `start <= time <= end`.

    Unlike `select_readings`, every filter is required, so an API caller can't
    accidentally pull a whole run.
    """
    return select_readings(run_id, data_type_names=data_type_names).where(
        data_table.c.time >= start, data_table.c.time <= end
    )


def select_data_types() -> Select[*tuple[Any, ...]]:
    """Penelope's sensor types, by name."""
    return select(data_type_table.c.name, data_type_table.c.unit).order_by(
        data_type_table.c.name
    )


def select_penelope_runs() -> Select[*tuple[Any, ...]]:
    """Every Penelope run, newest first: `run_id` (`run.id`, a uuid) and `time`.

    `run."runId"` is left out on purpose: it isn't unique.
    """
    return select(run_table.c.id.label("run_id"), run_table.c.time).order_by(
        run_table.c.time.desc().nulls_last(), run_table.c.id
    )


def select_penelope_runs_by_ids(run_ids: Collection[str]) -> Select[*tuple[Any, ...]]:
    """`select_penelope_runs`, limited to the given run ids."""
    return select_penelope_runs().where(run_table.c.id.in_(list(run_ids)))
