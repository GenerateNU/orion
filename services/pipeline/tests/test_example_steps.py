"""Steps are tested through `transform` (pure pandas), so no database is needed."""

import pandas as pd

from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.example_ingest_step import ExampleIngestStep
from orion_pipeline.steps.step_registry import ordered_steps


def test_dependencies_run_first():
    names = [step.name for step in ordered_steps()]
    assert names.index("example_ingest") < names.index("example_estimate")


def test_example_ingest_transform():
    step = ExampleIngestStep(reader=None, writer=None)
    raw = pd.DataFrame({"raw_tag": ["VCU/CarState/speed"], "values": [[12.5]]})

    cleaned = step.transform(raw, RunContext(run_id="run-1"))

    assert cleaned.to_dict("records") == [
        {"run_id": "run-1", "signal": "vcu/carstate/speed", "value": 12.5}
    ]
