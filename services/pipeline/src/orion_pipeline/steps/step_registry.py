from graphlib import TopologicalSorter

from orion_pipeline.steps.base_step import PipelineStep

STEPS: dict[str, type[PipelineStep]] = {}


def register_step(step_cls: type[PipelineStep]) -> type[PipelineStep]:
    """Class decorator that adds a step to the DAG."""
    STEPS[step_cls.name] = step_cls
    return step_cls


def ordered_steps() -> list[type[PipelineStep]]:
    """Every registered step, dependencies first."""
    graph = {name: step.depends_on for name, step in STEPS.items()}
    return [STEPS[name] for name in TopologicalSorter(graph).static_order()]
