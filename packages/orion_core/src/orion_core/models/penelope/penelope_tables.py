"""Penelope's tables, declared by hand on their OWN MetaData.

Alembic only sees Orion's `Base.metadata`, so it can never touch these.
The same definitions work for real Penelope and penelope2.
"""

from sqlalchemy import Column, DateTime, MetaData, String, Table
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
