from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd

from orion_backend.derived_metrics.alignment import DEFAULT_GAP_FACTOR, align_inputs
from orion_backend.schemas.sensor_schema import SensorSeries


class DerivedMetric(ABC):
    """A metric computed on request from Penelope sensors.

    Each input is a DataFrame indexed by time with one column per position in
    Penelope's `values[]` (e.g. 0 = lat, 1 = lon). NaN outputs are dropped.
    """

    name: ClassVar[str]
    unit: ClassVar[str]
    inputs: ClassVar[tuple[str, ...]]
    # Input whose timestamps drive the output rows; None = the most-sampled
    # linear one. Set it to the input whose timing matters most (e.g. brake
    # for braking metrics), since only the other inputs are interpolated.
    base: ClassVar[str | None] = None
    # A gap longer than this x a topic's median spacing is a dropout (NaN).
    gap_factor: ClassVar[float] = DEFAULT_GAP_FACTOR

    def align(self, inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Put the inputs onto one shared time index (see `alignment`).

        Columns are (topic, position), so `aligned[(topic, 0)]` is a topic's
        first value as a Series. Prefer that over `aligned[topic][0]`, which
        type checkers see as Any.
        """
        return align_inputs(inputs, self.base, self.gap_factor)

    @abstractmethod
    def compute(self, aligned: pd.DataFrame) -> pd.Series:
        """Pure pandas, no I/O. This is the part to unit test."""

    def run(self, inputs: dict[str, SensorSeries]) -> SensorSeries:
        """Aligns and computes the metric from raw sensor series."""
        aligned = self.align(_to_frames(inputs))
        if aligned.empty:
            return SensorSeries(time=[], values=[])
        return _to_series(self.compute(aligned).dropna())


def _to_frames(inputs: dict[str, SensorSeries]) -> dict[str, pd.DataFrame]:
    """One time-indexed frame per series, a column per `values[]` position."""
    return {
        name: pd.DataFrame(s.values, index=s.time, dtype=float)
        for name, s in inputs.items()
    }


def _to_series(result: pd.Series) -> SensorSeries:
    """A computed metric as a single-value `SensorSeries`."""
    return SensorSeries(
        time=[t.to_pydatetime() for t in result.index],
        values=[[value] for value in result.tolist()],
    )
