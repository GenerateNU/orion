from abc import ABC, abstractmethod
from typing import ClassVar, Literal

import pandas as pd

from orion_pipeline.clients.base_client import BaseClient
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext


class PipelineStep(ABC):
    """One unit of pipeline work: extract → transform → load.

    Steps never pass DataFrames to each other. Each one writes its output
    table to OrionDB, and the next step reads it back from there. That way
    any step can be re-run on its own.
    """

    name: ClassVar[str]
    depends_on: ClassVar[tuple[str, ...]] = ()
    reads_from: ClassVar[Literal["penelope", "oriondb"]]
    output_table: ClassVar[str]

    def __init__(self, reader: BaseClient, writer: OrionDBClient):
        self.reader = reader
        self.writer = writer

    @abstractmethod
    def extract(self, ctx: RunContext) -> pd.DataFrame:
        """Read inputs through `self.reader`."""

    @abstractmethod
    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Pure pandas, no I/O. This is the part to unit test."""

    def load(self, df: pd.DataFrame, ctx: RunContext) -> None:
        self.writer.replace_for_run(self.output_table, ctx.run_id, df)

    def run(self, ctx: RunContext) -> None:
        self.load(self.transform(self.extract(ctx), ctx), ctx)
