import pandas as pd
from sqlalchemy import Engine, Executable


class BaseClient:
    """Sync database access that speaks DataFrames. Steps use clients, never sessions."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def read_frame(self, stmt: Executable) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql(stmt, conn)
