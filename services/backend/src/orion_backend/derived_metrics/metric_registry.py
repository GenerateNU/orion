from orion_backend.derived_metrics.base_metric import DerivedMetric

METRICS: dict[str, DerivedMetric] = {}


def register_metric(metric_cls: type[DerivedMetric]) -> type[DerivedMetric]:
    """Class decorator that makes a metric available to the API."""
    METRICS[metric_cls.name] = metric_cls()
    return metric_cls
