from collections.abc import Iterator
from typing import Any

import pandas as pd
from sqlalchemy import Engine, Select, tuple_


class BaseClient:
    """Sync database access that speaks DataFrames. Steps use clients, never sessions."""

    def __init__(self, engine: Engine, page_size: int):
        self.engine = engine
        # Most rows any one read pulls at once (`Settings.pipeline_page_size`).
        self.page_size = page_size

    def read_frame(self, stmt: Select[*tuple[Any, ...]]) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql(stmt, conn)

    def read_page(
        self,
        stmt: Select[*tuple[Any, ...]],
        key: tuple[str, ...],
        after: tuple[Any, ...] | None,
    ) -> pd.DataFrame:
        """Read the next `self.page_size` rows of `stmt` after the cursor `after`.

        Keyset pagination: the rows are ordered by `key` and filtered to
        `key > after`, so every page costs the same no matter how deep into the
        run it is (OFFSET would rescan all earlier rows). `key` names columns
        selected by `stmt`, and together they must be unique, or rows that tie
        at a page boundary get skipped.
        """
        cols = [stmt.selected_columns[name] for name in key]
        if after is not None:
            stmt = stmt.where(tuple_(*cols) > tuple_(*after))
        return self.read_frame(
            stmt.order_by(None).order_by(*cols).limit(self.page_size)
        )

    def iter_pages(
        self, stmt: Select[*tuple[Any, ...]], key: tuple[str, ...]
    ) -> Iterator[pd.DataFrame]:
        """Yield `stmt`'s rows one page at a time, paged by `key`.

        Each page is read on its own short connection, and the next one isn't
        read until the caller is done with the current one.
        """
        after: tuple[Any, ...] | None = None
        while True:
            page = self.read_page(stmt, key, after)
            if page.empty:
                return
            yield page
            if len(page) < self.page_size:
                return
            next_after = tuple(page[list(key)].iloc[-1])
            if next_after == after:
                raise RuntimeError(f"cursor did not advance past {after}")
            after = next_after
