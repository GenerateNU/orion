from orion_backend.derived_metrics.alignment import validate_settings
from orion_backend.derived_metrics.base_metric import DerivedMetric

METRICS: dict[str, DerivedMetric] = {}


def register_metric(metric_cls: type[DerivedMetric]) -> type[DerivedMetric]:
    """Class decorator that makes a metric available to the API.

    Checks the metric's alignment settings here, so a bad one fails at import
    instead of on the first request.
    """
    try:
        validate_settings(metric_cls.inputs, metric_cls.base, metric_cls.gap_factor)
    except ValueError as e:
        raise ValueError(f"metric {metric_cls.name!r}: {e}") from None
    METRICS[metric_cls.name] = metric_cls()
    return metric_cls
