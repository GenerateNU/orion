from typing import Generic, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import Table, insert
from sqlalchemy.engine import Engine

from .schema import data_table
from penelope.models import DataPoint

ModelT = TypeVar("ModelT", bound=BaseModel)


class Repository(Generic[ModelT]):
    """Generic write-only repository: one Pydantic model <-> one Table."""

    def __init__(self, engine: Engine, model: Type[ModelT], table: Table):
        self.engine = engine
        self.model = model
        self.table = table

    def write(self, record: ModelT) -> None:
        self.write_many([record])

    def write_many(self, records: list[ModelT]) -> None:
        if not records:
            return
        for r in records:
            if not isinstance(r, self.model):
                raise TypeError(f"expected {self.model.__name__}, got {type(r).__name__}")
        rows = [r.model_dump(by_alias=True) for r in records]
        with self.engine.begin() as conn:
            conn.execute(insert(self.table), rows)


class DataPointRepository(Repository[DataPoint]):
    """Write-only repository for the `data` table."""

    def __init__(self, engine: Engine):
        super().__init__(engine, DataPoint, data_table)