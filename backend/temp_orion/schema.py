from sqlalchemy import Column, Integer, MetaData, String, Table, Text

metadata = MetaData()


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