"""Copy Penelope into the penelope_copy database, adding only rows the copy doesn't have yet.

The copy has Penelope's exact tables, so if Penelope goes down, pointing
PENELOPE_DATABASE_URL at the copy is all it takes to keep Orion running.
Re-running it only copies new rows; an interrupted sync picks up where it stopped.

    uv run python -m orion_core.db.scripts.penelope_sync [--since 2026-08-01] [--run ID ...]
"""

import argparse
import logging
from collections.abc import Collection
from datetime import UTC, datetime
from typing import Any, cast

import psycopg
from psycopg import sql
from sqlalchemy import Engine, Table, select, text, tuple_
from sqlalchemy.dialects.postgresql import insert

from orion_core.db.engines import make_sync_engine
from orion_core.models.penelope import (
    data_table,
    data_type_table,
    penelope_metadata,
    run_table,
)
from orion_core.settings import get_settings

logger = logging.getLogger(__name__)


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


def _copy_whole_table(penelope: Engine, copy_engine: Engine, table: Table) -> None:
    """Upsert every row of a small table into the copy.

    Rows the copy already has are overwritten with Penelope's version. Reads the
    whole table in one query, so it's only for small tables; `data` is copied
    page by page in `_copy_run`.
    """
    with penelope.connect() as conn:
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


def _copy_run(
    penelope: Engine, copy_engine: Engine, run_id: str, page_size: int
) -> int:
    """Copy the run's `data` rows the copy doesn't have yet. Returns rows copied.

    Pages are keyset-paginated on (time, dataTypeName), which is unique within a
    run, and each page is written with COPY in its own transaction.
    """
    key = (data_table.c.time, data_table.c.dataTypeName)
    stmt = (
        select(data_table)
        .where(data_table.c.runId == run_id)
        .order_by(*key)
        .limit(page_size)
    )
    copy_sql = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(data_table.name),
        sql.SQL(", ").join(sql.Identifier(c.name) for c in data_table.columns),
    )
    after = _last_copied(copy_engine, run_id)
    copied = 0
    while True:
        page = stmt if after is None else stmt.where(tuple_(*key) > tuple_(*after))
        with penelope.connect() as conn:
            rows = conn.execute(page).all()
        if not rows:
            return copied
        with copy_engine.begin() as conn:
            raw = cast(psycopg.Connection[Any], conn.connection.driver_connection)
            with raw.cursor() as cur, cur.copy(copy_sql) as copy:
                for row in rows:
                    copy.write_row(tuple(row))
        copied += len(rows)
        logger.info("run %s: copied %d rows so far", run_id, copied)
        if len(rows) < page_size:
            return copied
        after = (rows[-1].time, rows[-1].dataTypeName)


def sync(
    penelope: Engine,
    copy_engine: Engine,
    page_size: int,
    since: datetime | None = None,
    run_ids: Collection[str] | None = None,
) -> dict[str, int]:
    """Copy everything Penelope has that the copy doesn't. Returns rows copied per run.

    `since` and `run_ids`, if given, limit which runs' `data` is copied (`run` and
    `data_type` are small, so they're always copied whole).
    """
    _create_tables(copy_engine)
    _copy_whole_table(penelope, copy_engine, run_table)
    _copy_whole_table(penelope, copy_engine, data_type_table)

    stmt = select(run_table.c.id)
    if since is not None:
        stmt = stmt.where(run_table.c.time >= since)
    with penelope.connect() as conn:
        selected = list(conn.execute(stmt).scalars())
    if run_ids is not None:
        missing = set(run_ids) - set(selected)
        if missing:
            raise ValueError(f"runs not in Penelope (or before --since): {missing}")
        selected = [r for r in selected if r in run_ids]

    copied: dict[str, int] = {}
    for run_id in selected:
        n = _copy_run(penelope, copy_engine, run_id, page_size)
        if n:
            copied[run_id] = n
            logger.info("run %s: copied %d new rows", run_id, n)
    logger.info("sync done: %d runs had new rows", len(copied))
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "--since",
        type=lambda s: datetime.fromisoformat(s).replace(tzinfo=UTC),
        help="only copy runs that started on/after this UTC date, e.g. 2026-08-01",
    )
    parser.add_argument(
        "--run", nargs="+", dest="run_ids", help="only copy these run ids"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.penelope_database_url:
        raise SystemExit("PENELOPE_DATABASE_URL is not set")
    if not settings.penelope_copy_database_url:
        raise SystemExit("PENELOPE_COPY_DATABASE_URL is not set")
    sync(
        make_sync_engine(settings.penelope_database_url, read_only=True),
        make_sync_engine(settings.penelope_copy_database_url),
        settings.pipeline_page_size,
        since=args.since,
        run_ids=args.run_ids,
    )


if __name__ == "__main__":
    main()
