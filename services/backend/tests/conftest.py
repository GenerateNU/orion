from collections.abc import Iterator

import pytest

from orion_backend.derived_metrics.metric_registry import METRICS


@pytest.fixture(autouse=True)
def isolated_metrics() -> Iterator[None]:
    """Undo any metric a test registers, so tests don't see each other's."""
    saved = dict(METRICS)
    yield
    METRICS.clear()
    METRICS.update(saved)
