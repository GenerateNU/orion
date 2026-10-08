
import numpy as np
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine

from .schema import cleaned_data_table, data_table


class DataPointRepository:
    """Generic write-only repository: np array <-> data and cleaned data tables."""

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

    def write_cleaned(self, rows, conn=None) -> int:
            """Insert (runId, time, sensor, value) rows into cleaned_data.

            Pass conn to write inside the caller's transaction, so the caller
            decides when everything commits or rolls back. Without it, this opens
            and commits its own transaction.

            Returns:
                The number of rows actually inserted (rows already present,
                per the primary key, are silently skipped).
            """
            if len(rows) == 0:
                return 0

            dicts = [
                {"runId": row[0], "time": row[1], "sensor": row[2], "value": row[3]}
                for row in rows
            ]

            # Same ON CONFLICT + RETURNING approach as write_many, for the same reasons.
            stmt = (
                insert(cleaned_data_table)
                .on_conflict_do_nothing()
                .returning(cleaned_data_table.c.time)
            )
            if conn is not None:
                return len(conn.execute(stmt, dicts).all())
            with self.engine.begin() as ownconn:
                return len(ownconn.execute(stmt, dicts).all())