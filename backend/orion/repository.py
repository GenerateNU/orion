from typing import Generic, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from .schema import data_table
from penelope.models import DataPoint

import numpy as np

class DataPointRepository:
    """Generic write-only repository: np array <-> one Table."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.table = data_table

    def write(self, rows: np.ndarray) -> int:
        return self.write_many(rows.reshape(1, -1))

    def write_many(self, rows: np.ndarray) -> int:
        """Insert multiple rows from a 2D NumPy array.

        Each row must be [time, dataTypeName, runId, values], matching
        PenelopeClient's array output.

        Returns:
            The number of rows actually inserted (rows already present,
            per the primary key, are silently skipped).
        """
        if rows.size == 0:
            return 0

        # Convert each array row into a dict matching the table's columns,
        # since SQLAlchemy's insert() needs dicts, not raw array rows.
        dicts = [
            {
                "time": row[0],
                "dataTypeName": row[1],
                "runId": row[2],
                "values": row[3],
            }
            for row in rows
        ]

        # ON CONFLICT DO NOTHING makes re-writing the same window a no-op
        # instead of an error, since (time, dataTypeName, runId) is the
        # table's primary key.
        #
        # RETURNING is what keeps this fast: SQLAlchemy won't batch an
        # ON CONFLICT insert into multi-row VALUES without it, and falls back
        # to one network round trip per row. It also gives an accurate insert
        # count, since skipped rows return nothing.
        stmt = (
            insert(self.table)
            .on_conflict_do_nothing()
            .returning(self.table.c.time)
        )
        with self.engine.begin() as conn:
            return len(conn.execute(stmt, dicts).all())