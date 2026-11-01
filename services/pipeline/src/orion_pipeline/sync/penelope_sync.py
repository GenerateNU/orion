"""Copy Penelope into the penelope_copy database, adding only rows the copy doesn't have yet.

The copy has Penelope's exact tables, so if Penelope goes down, pointing
PENELOPE_DATABASE_URL at the copy is all it takes to keep Orion running.
"""

import logging
from collections.abc import Collection
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, Table, select, text
from sqlalchemy.dialects.postgresql import insert

from orion_core.models.penelope import (
    data_table,
    data_type_table,
    penelope_metadata,
    run_table,
)
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient

logger = logging.getLogger(__name__)

# `data` is paged by this, so each run's sync starts just past its last copied row.
DATA_KEY = ("time", "dataTypeName")


def _create_tables(copy_engine: Engine) -> None:
    """Create Penelope's tables in the copy if they aren't there yet."""
    penelope_metadata.create_all(copy_engine)
    # Penelope's PK starts with time, so add one starting with runId to make
    # `_last_copied` an index lookup instead of a scan of the whole table.
    with copy_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_data_run_time_type "
                'ON data ("runId", time, "dataTypeName")'
            )
        )


def _copy_whole_table(
    penelope: PenelopeClient, copy_engine: Engine, table: Table
) -> None:
    """Upsert every row of a small table into the copy.

    Rows the copy already has are overwritten with Penelope's version. Reads the
    whole table in one query, so it's only for small tables; `data` is copied
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


def sync(
    penelope: PenelopeClient,
    copy: OrionDBClient,
    since: datetime | None = None,
    run_ids: Collection[str] | None = None,
) -> dict[str, int]:
    """Copy everything Penelope has that the copy doesn't. Returns rows copied per run.

    `copy` is an OrionDBClient on the penelope_copy engine, used only for `append`.
    `since` and `run_ids`, if given, limit which runs' `data` is copied (`run` and
    `data_type` are small, so they're always copied whole).
    """
    _create_tables(copy.engine)
    _copy_whole_table(penelope, copy.engine, run_table)
    _copy_whole_table(penelope, copy.engine, data_type_table)

    copied: dict[str, int] = {}
    runs = penelope.list_runs()
    if since is not None:
        runs = runs[runs["time"] >= since]
    if run_ids is not None:
        missing = set(run_ids) - set(runs["run_id"])
        if missing:
            raise ValueError(f"runs not in Penelope (or before --since): {missing}")
        runs = runs[runs["run_id"].isin(run_ids)]
    for run_id in runs["run_id"]:
        stmt = select(data_table).where(data_table.c.runId == run_id)
        after = _last_copied(copy.engine, run_id)
        for page in penelope.iter_pages(stmt, DATA_KEY, after=after):
            copy.append(data_table.name, page)
            copied[run_id] = copied.get(run_id, 0) + len(page)
        if run_id in copied:
            logger.info("run %s: copied %d new rows", run_id, copied[run_id])
    logger.info("sync done: %d runs had new rows", len(copied))
    return copied
