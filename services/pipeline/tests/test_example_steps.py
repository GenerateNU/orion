"""Steps are tested through `transform` (pure pandas), so no database is needed."""

from unittest.mock import Mock

import pandas as pd
import pytest
from sqlalchemy import Engine, Select

from orion_pipeline.clients.base_client import BaseClient
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps import step_registry
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.example_ingest_step import ExampleIngestStep
from orion_pipeline.steps.step_registry import ordered_steps, register_step


def test_dependencies_run_first(monkeypatch):
    # An empty registry, so the test doesn't depend on which real steps exist.
    monkeypatch.setattr(step_registry, "STEPS", {})

    # Registered downstream-first, so passing means the sort did the ordering.
    @register_step
    class _Downstream(PipelineStep):
        name = "downstream"
        depends_on = ("upstream",)

    @register_step
    class _Upstream(PipelineStep):
        name = "upstream"

    assert [step.name for step in ordered_steps()] == ["upstream", "downstream"]


def test_pipeline_registers_clean_step():
    import orion_pipeline.steps  # noqa: F401  (importing registers every step)

    assert "clean_step" in step_registry.STEPS


def test_example_ingest_transform():
    step = ExampleIngestStep(
        reader=Mock(spec=PenelopeClient), writer=Mock(spec=OrionDBClient)
    )
    raw = pd.DataFrame({"raw_tag": ["VCU/CarState/speed"], "values": [[12.5]]})

    cleaned = step.transform(raw, RunContext(run_id="run-1"))

    assert cleaned.to_dict("records") == [
        {"run_id": "run-1", "signal": "vcu/carstate/speed", "value": 12.5}
    ]


class _RecordingStep(ExampleIngestStep):
    """Yields `pages` and records every call, so `run` can be tested without
    a database."""

    def __init__(self, pages: list[pd.DataFrame]):
        super().__init__(
            reader=Mock(spec=PenelopeClient), writer=Mock(spec=OrionDBClient)
        )
        self._pages = pages
        self.calls: list[tuple] = []

    def extract(self, ctx):
        for page in self._pages:
            self.calls.append(("extract",))
            yield page

    def transform(self, df, ctx):
        return df

    def prepare(self, ctx):
        self.calls.append(("prepare",))

    def write(self, df, ctx):
        self.calls.append(("write", df["time"].tolist()))


def test_run_writes_each_page_before_extracting_the_next():
    step = _RecordingStep([pd.DataFrame({"time": [1, 2]}), pd.DataFrame({"time": [3]})])

    step.run(RunContext(run_id="run-1"))

    assert step.calls == [
        ("prepare",),
        ("extract",),
        ("write", [1, 2]),
        ("extract",),
        ("write", [3]),
    ]


def _client_over(rows: pd.DataFrame, cursors: list) -> BaseClient:
    """A client whose `read_page` slices `rows` in memory and records each cursor."""
    client = BaseClient(engine=Mock(spec=Engine), page_size=2)

    def read_page(stmt, key, after):
        cursors.append(after)
        page = rows if after is None else rows[rows["time"] > after[0]]
        return page.head(client.page_size)

    client.read_page = read_page
    return client


def test_iter_pages_yields_by_cursor():
    cursors: list = []
    client = _client_over(pd.DataFrame({"time": [1, 2, 3, 4, 5]}), cursors)

    pages = [
        page["time"].tolist()
        for page in client.iter_pages(Mock(spec=Select), ("time",))
    ]

    assert pages == [[1, 2], [3, 4], [5]]
    assert cursors == [None, (2,), (4,)]


def test_iter_pages_raises_when_cursor_does_not_advance():
    client = BaseClient(engine=Mock(spec=Engine), page_size=2)
    rows = pd.DataFrame({"time": [1, 2, 3]})
    client.read_page = lambda stmt, key, after: rows.head(2)  # ignores `after`

    with pytest.raises(RuntimeError, match="did not advance"):
        list(client.iter_pages(Mock(spec=Select), ("time",)))
