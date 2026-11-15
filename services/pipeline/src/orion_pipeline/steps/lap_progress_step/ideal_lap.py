from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from orion_pipeline.steps.lap_step.lap_utils import (
    Gate,
    apply_min_lap_time,
    distance_driven,
    find_crossings,
    headings,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class IdealLap:
    """The chosen lap, redrawn with evenly spaced points from the gate.

    'percent[i]' is how far around the lap point i is, from 0 at the gate. The
    path is a loop: after its last point it returns to the first.
    """

    # The `laps` row the path starts in. For a loop cut by the fallback (see
    # `build_ideal_lap`), that lap can hold more than this one loop.
    lap_id: int
    x: FloatArray
    y: FloatArray
    percent: FloatArray
    length_m: float


def assign_lap_ids(times: pd.Series, laps: pd.DataFrame) -> NDArray[np.int64]:
    """The 'lap_id' of the lap each time falls in.

    A lap covers [start_time, end_time), and the last lap also covers its end.
    Times before the first lap get the first lap.
    """
    starts = laps["start_time"].to_numpy()
    index = np.searchsorted(starts, times.to_numpy(), side="right") - 1
    lap_ids = laps["lap_id"].to_numpy(dtype=np.int64)
    return lap_ids[np.clip(index, 0, len(lap_ids) - 1)]


def lap_stats(positions: pd.DataFrame, laps: pd.DataFrame) -> pd.DataFrame:
    """Each lap's time, driven distance, and longest hole in its data.

    Args:
        positions: The run's points in time order, with time, x and y.
        laps: The run's 'laps' rows, in order.

    Returns:
        'laps' with 'duration_s', 'length_m' and 'max_gap_s' added. The gap counts
        the edges too: lap start to first point, and last point to lap end. A lap
        with no points has an infinite gap.
    """
    # Only each lap's own points, in [start_time, end_time): unlike
    # 'assign_lap_ids', points before the first lap or after the last one don't
    # count toward them. Loops cut by the fallback don't cover the whole run, and
    # the drive before the first pass must not make loop 1 look twice as long.
    times = positions["time"]
    starts = pd.DatetimeIndex(laps["start_time"])
    ends = pd.DatetimeIndex(laps["end_time"])
    lengths: list[float] = []
    gaps: list[float] = []
    for i in range(len(laps)):
        points = positions[(times >= starts[i]) & (times < ends[i])]
        if points.empty:
            lengths.append(0.0)
            gaps.append(np.inf)
            continue
        edges = pd.Series([starts[i], *points["time"], ends[i]])
        gaps.append(float(edges.diff().dt.total_seconds().max()))
        x = points["x"].to_numpy(dtype=np.float64)
        y = points["y"].to_numpy(dtype=np.float64)
        lengths.append(float(distance_driven(x, y)[-1]))
    return laps.assign(
        duration_s=(ends - starts).total_seconds(), length_m=lengths, max_gap_s=gaps
    )


def pick_median_lap(
    stats: pd.DataFrame,
    *,
    max_gap_s: float,
    max_length_ratio: float,
    skip_ends: bool = True,
) -> int | None:
    """The lap_id of the ideal lap, or None if no lap qualifies.

    1. Full data: no hole longer than 'max_gap_s', and not the first or last lap
       when 'skip_ends' (laps from the laps table start or end wherever the run
       does, not at the gate).
    2. Single loop: no longer than 'max_length_ratio' times the shortest
       full-data lap.
    3. The median lap time of what's left. With an even count, the faster of the
       two middle laps.

    Args:
        stats: Output of `lap_stats`, in lap order.
        max_gap_s: Longest allowed hole in a lap's data, in seconds.
        max_length_ratio: Longest allowed lap, as a multiple of the shortest.
        skip_ends: Leave out the first and last laps.

    Returns:
        None when no lap passes steps 1 and 2.
    """
    candidates = stats.iloc[1:-1] if skip_ends else stats
    full_data = candidates[candidates["max_gap_s"] <= max_gap_s]
    if full_data.empty:
        return None
    shortest_m = full_data["length_m"].min()
    single_loop = full_data[full_data["length_m"] <= shortest_m * max_length_ratio]
    ranked = single_loop.sort_values(["duration_s", "lap_id"], kind="stable")
    return int(ranked["lap_id"].iloc[(len(ranked) - 1) // 2])


def gate_at(positions: pd.DataFrame, index: int, half_width_m: float) -> Gate | None:
    """A gate across the car's path at 'positions' row 'index', or None if the car
    isn't moving there."""
    x = positions["x"].to_numpy(dtype=np.float64)
    y = positions["y"].to_numpy(dtype=np.float64)
    hx, hy = headings(x, y)
    if hx[index] == 0 and hy[index] == 0:
        return None
    return Gate(
        x=float(x[index]),
        y=float(y[index]),
        heading_x=float(hx[index]),
        heading_y=float(hy[index]),
        half_width_m=half_width_m,
    )


def loops_through_gate(
    positions: pd.DataFrame, gate: Gate, *, min_loop_time_s: float
) -> pd.DataFrame:
    """Every full loop from one pass through 'gate' to the next, shaped like 'laps'
    rows ('lap_id', numbered from 1, 'start_time', 'end_time').

    Passes less than 'min_loop_time_s' after the previous one are ignored, like the
    lap step's minimum lap time. The stretches before the first pass and after the
    last aren't full loops, so they're left out.
    """
    x = positions["x"].to_numpy(dtype=np.float64)
    y = positions["y"].to_numpy(dtype=np.float64)
    times = positions["time"]
    passes = times.iloc[find_crossings(x, y, gate)].tolist()
    if not passes:
        return pd.DataFrame(columns=["lap_id", "start_time", "end_time"])
    kept = [passes[0], *apply_min_lap_time(passes[0], passes[1:], min_loop_time_s)]
    return pd.DataFrame(
        {
            "lap_id": range(1, len(kept)),
            "start_time": kept[:-1],
            "end_time": kept[1:],
        }
    )


def build_ideal_lap(
    positions: pd.DataFrame,
    laps: pd.DataFrame,
    *,
    max_gap_s: float,
    max_length_ratio: float,
    spacing_m: float,
    fallback_gate: Callable[[], Gate | None] | None = None,
    min_loop_time_s: float = 0.0,
) -> IdealLap | None:
    """The run's ideal lap, redrawn with a point every `spacing_m` meters.

    Normally the run's median lap (see 'pick_median_lap'). When no lap qualifies,
    for example a run with only one or two laps, single loops are cut straight
    from the positions instead: one per pass through 'fallback_gate()', then the
    same full-data, single-loop and median rules choose between them.

    Args:
        positions: The run's points in time order, with time, x and y.
        laps: The run's laps rows, in order.
        max_gap_s: See pick_median_lap.
        max_length_ratio: See pick_median_lap.
        spacing_m: Distance between the ideal lap's points, in meters.
        fallback_gate: Builds the gate to cut loops at, only if it's needed.
            Returns None, or isn't given, when there's nowhere to cut.
        min_loop_time_s: See loops_through_gate.

    Returns:
        None if no lap or loop qualifies.
    """
    if positions.empty or laps.empty:
        return None
    lap_id = pick_median_lap(
        lap_stats(positions, laps),
        max_gap_s=max_gap_s,
        max_length_ratio=max_length_ratio,
    )
    if lap_id is not None:
        points = positions[assign_lap_ids(positions["time"], laps) == lap_id]
        return _redraw(points, lap_id, spacing_m)

    gate = fallback_gate() if fallback_gate else None
    if gate is None:
        return None
    loops = loops_through_gate(positions, gate, min_loop_time_s=min_loop_time_s)
    if loops.empty:
        return None
    loop_id = pick_median_lap(
        lap_stats(positions, loops),
        max_gap_s=max_gap_s,
        max_length_ratio=max_length_ratio,
        skip_ends=False,
    )
    if loop_id is None:
        return None
    loop = loops[loops["lap_id"] == loop_id].iloc[0]
    times = positions["time"]
    points = positions[(times >= loop["start_time"]) & (times < loop["end_time"])]
    start_lap = assign_lap_ids(pd.Series([loop["start_time"]]), laps)[0]
    return _redraw(points, int(start_lap), spacing_m)


def _redraw(points: pd.DataFrame, lap_id: int, spacing_m: float) -> IdealLap:
    """'points' as an IdealLap with a point every 'spacing_m' meters."""
    x = points["x"].to_numpy(dtype=np.float64)
    y = points["y"].to_numpy(dtype=np.float64)
    s = distance_driven(x, y)
    length_m = float(s[-1])
    grid = np.arange(0.0, length_m, spacing_m)
    return IdealLap(
        lap_id=lap_id,
        x=np.interp(grid, s, x),
        y=np.interp(grid, s, y),
        percent=100.0 * grid / length_m,
        length_m=length_m,
    )
