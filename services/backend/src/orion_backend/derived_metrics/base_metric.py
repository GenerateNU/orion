from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd

from orion_backend.schemas.sensor_schema import SensorSeries


class DerivedMetric(ABC):
    """A metric computed on request from Penelope sensors.

    Each input is a DataFrame indexed by time with one column per position in
    Penelope's `values[]` (e.g. 0 = lat, 1 = lon). NaN outputs are dropped.
    """

    name: ClassVar[str]
    unit: ClassVar[str]
    inputs: ClassVar[tuple[str, ...]]

    @abstractmethod
    def align(self, inputs: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Put the inputs onto one shared time index."""

    @abstractmethod
    def compute(self, aligned: pd.DataFrame) -> pd.Series:
        """Pure pandas, no I/O. This is the part to unit test."""

    def run(self, inputs: dict[str, SensorSeries]) -> SensorSeries:
        """Aligns and computes the metric from raw sensor series."""
        frames = {
            name: pd.DataFrame(s.values, index=s.time, dtype=float)
            for name, s in inputs.items()
        }
        result = self.compute(self.align(frames)).dropna()
        return SensorSeries(
            time=[t.to_pydatetime() for t in result.index],
            values=[[value] for value in result.tolist()],
        )
