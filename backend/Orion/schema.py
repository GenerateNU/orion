from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text

signals_table = Table(
    "signals",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("raw_tag", String, nullable=False, unique=True),
    Column("name", String, nullable=False, unique=True),
    Column("display_name", String, nullable=False),
    Column("description", Text, nullable=False),
    Column("unit", String, nullable=True),
)