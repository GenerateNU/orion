from sqlalchemy import Column, DateTime, MetaData, String, Table
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION
from sqlalchemy.engine import Engine

metadata = MetaData()

data_table = Table(
    "data",
    metadata,
    Column("dataTypeName", String, nullable=False),
    Column("time", DateTime(timezone=True), nullable=False),
    Column("runId", String, nullable=False),
    Column("values", ARRAY(DOUBLE_PRECISION), nullable=False),
)


def create_tables(engine: Engine) -> None:
    """Create all tables in this module if they don't already exist."""
    metadata.create_all(engine, checkfirst=True)