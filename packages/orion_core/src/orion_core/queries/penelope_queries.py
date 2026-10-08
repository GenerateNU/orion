"""Penelope SELECT builders. They build statements but never run them, so the
async backend and the sync pipeline can share them."""

from sqlalchemy import Select, select

from orion_core.db.penelope.penelope_tables import data_table


def select_readings(run_id: str, limit: int | None = None) -> Select:
    stmt = (
        select(
            data_table.c.time,
            data_table.c.dataTypeName.label("raw_tag"),
            data_table.c["values"],
        )
        .where(data_table.c.runId == run_id)
        .order_by(data_table.c.time)
    )
    return stmt.limit(limit) if limit else stmt
