"""Copy Penelope into OrionDB's `penelope` schema, adding only rows the copy doesn't have yet."""

import logging
from typing import Any

from sqlalchemy import Engine, Table, select
from sqlalchemy.dialects.postgresql import insert

from orion_core.models.penelope import data_table, data_type_table, run_table
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient

logger = logging.getLogger(__name__)

# Where the copy lives in OrionDB (created by the copy_penelope migration).
COPY_SCHEMA = "penelope"
# `data` is paged by this, so each run's sync starts just past its last copied row.
DATA_KEY = ("time", "dataTypeName")


def _copy_whole_table(
    penelope: PenelopeClient, copy_engine: Engine, table: Table
) -> None:
    """Copy every row of the small tables if there are changes.
    Rows the copy already has are overwritten with Penelope's version.

    Only for small tables: reads the whole table in one query. `data` is copied
    page by page in `sync()`.
    """
    with penelope.engine.connect() as conn:
        rows = [dict(row._mapping) for row in conn.execute(select(table))]
    if not rows:
        return
    stmt = insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=list(table.primary_key.columns),
        set_={
            c.name: stmt.excluded[c.name] for c in table.columns if not c.primary_key
        },
    )
    with copy_engine.begin() as conn:
        conn.execute(stmt)


def _last_copied(copy_engine: Engine, run_id: str) -> tuple[Any, ...] | None:
    """The run's last copied (time, dataTypeName), or None if none of it is copied yet."""
    stmt = (
        select(data_table.c.time, data_table.c.dataTypeName)
        .where(data_table.c.runId == run_id)
        .order_by(data_table.c.time.desc(), data_table.c.dataTypeName.desc())
        .limit(1)
    )
    with copy_engine.connect() as conn:
        row = conn.execute(stmt).first()
    return tuple(row) if row else None


def sync(penelope: PenelopeClient, oriondb: OrionDBClient) -> dict[str, int]:
    """Copy everything Penelope has that the copy doesn't. Returns rows copied per run."""
    # Points the Penelope table definitions at the `penelope` schema instead of `public`.
    copy_engine = oriondb.engine.execution_options(
        schema_translate_map={None: COPY_SCHEMA}
    )
    _copy_whole_table(penelope, copy_engine, run_table)
    _copy_whole_table(penelope, copy_engine, data_type_table)

    copied: dict[str, int] = {}
    for run_id in penelope.list_runs()["run_id"]:
        stmt = select(data_table).where(data_table.c.runId == run_id)
        after = _last_copied(copy_engine, run_id)
        for page in penelope.iter_pages(stmt, DATA_KEY, after=after):
            oriondb.append(data_table.name, page, schema=COPY_SCHEMA)
            copied[run_id] = copied.get(run_id, 0) + len(page)
        if run_id in copied:
            logger.info("run %s: copied %d new rows", run_id, copied[run_id])
    logger.info("sync done: %d runs had new rows", len(copied))
    return copied
