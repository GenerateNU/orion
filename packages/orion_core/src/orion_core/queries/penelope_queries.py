"""Penelope SELECT builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from collections.abc import Collection

from sqlalchemy import Select, select

from orion_core.models.penelope import data_table


def select_readings(
    run_id: str,
    limit: int | None = None,
    data_type_names: Collection[str] | None = None,
) -> Select:
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
