from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import ClassVar, Literal

import pandas as pd

from orion_pipeline.clients.base_client import BaseClient
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext


class PipelineStep(ABC):
    """One unit of pipeline work: extract → transform → write, one page at a time.

    Steps never pass DataFrames to each other. Each one writes its output
    table to OrionDB, and the next step reads it back from there. That way
    any step can be re-run on its own.

    Runs are too big to hold in memory, so `extract` yields pages of up to
    `page_size` rows, and `run` transforms and writes each page before the
    next one is extracted. The step owns the query and the pagination key;
    the client owns the connection and walks the query page by page.
    """

    name: ClassVar[str]
    depends_on: ClassVar[tuple[str, ...]] = ()
    reads_from: ClassVar[Literal["penelope", "oriondb"]]
    output_table: ClassVar[str]

    # Columns the input is paged by, in sort order, handed to the client.
    # Together they must be unique.
    pagination_key: ClassVar[tuple[str, ...]]
    # TODO: Read from config not hardcode!!!
    page_size: ClassVar[int] = 100_000

    def __init__(self, reader: BaseClient, writer: OrionDBClient):
        self.reader = reader
        self.writer = writer

    @abstractmethod
    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        """Return the input as pages, usually the reader's page iterator built
        with `self.pagination_key` and `self.page_size`. Steps that page some
        other way (time windows, multiple sources) can write their own generator."""

    @abstractmethod
    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Pure pandas, no I/O. This is the part to unit test."""

    def prepare(self, ctx: RunContext) -> None:
        """Runs once before the first page. Clears the run's old output so a
        re-run replaces it. Override if the step writes to multiple tables."""
        self.writer.delete_for_run(self.output_table, ctx.run_id)

    def write(self, df: pd.DataFrame, ctx: RunContext) -> None:
        """Writes one transformed page. Override if the step writes to multiple tables."""
        self.writer.append(self.output_table, df)

    def run(self, ctx: RunContext) -> None:
        """Runs the step in Prepare -> Transform -> Write order."""
        self.prepare(ctx)
        for page in self.extract(ctx):
            self.write(self.transform(page, ctx), ctx)
