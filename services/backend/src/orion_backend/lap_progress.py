"""How far through its lap the car is at each point (see docs/lap_progress.md)."""

from collections.abc import Sequence

from orion_core.models.orion import Lap


def reference_lap(laps: Sequence[Lap]) -> Lap:
    """The median lap by lap time. Of two middle laps, the one with the lower lap_id."""
    by_time = sorted(laps, key=lambda lap: lap.end_time - lap.start_time)
    middle = by_time[(len(by_time) - 1) // 2 : len(by_time) // 2 + 1]
    return min(middle, key=lambda lap: lap.lap_id)
