"""Penelope's tables, declared by hand on their OWN MetaData.

Alembic only sees Orion's `Base.metadata`, so it can never touch these.
The same definitions work for real Penelope and penelope2.
"""

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION

penelope_metadata = MetaData()

data_table = Table(
    "data",
    penelope_metadata,
    Column("time", DateTime(timezone=True), primary_key=True),
    Column("dataTypeName", String, primary_key=True),
    Column("runId", String, primary_key=True),
    Column("values", ARRAY(DOUBLE_PRECISION)),
)

data_type_table = Table(
    "data_type",
    penelope_metadata,
    Column("name", String, primary_key=True),
    Column("unit", String),
)

# One row per logging session. `id` (uuid text) is what `data."runId"` holds and what
# Orion stores as `run_id`. `"runId"` is a counter that is NOT unique, so Orion
# never uses it.
run_table = Table(
    "run",
    penelope_metadata,
    Column("id", String, primary_key=True),
    Column("runId", Integer),
    Column("driverName", String),
    Column("locationName", String),
    Column("notes", String),
    Column("time", DateTime(timezone=True)),
)
