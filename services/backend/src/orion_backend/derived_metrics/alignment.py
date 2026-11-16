"""Put a metric's input topics onto one shared time index.

Rows are the base input's timestamps plus every time a PREVIOUS input
changes value, so a short event between base samples (a fault, a state
change) keeps its exact start and end instead of being missed. The base is
the most-sampled LINEAR input (any input if none are LINEAR) unless the
metric names one.

Each input is filled at those rows by its `interp_for` kind:

LINEAR    interpolated between the samples either side of the row.
PREVIOUS  the last value at or before the row; never interpolated.

Every topic is treated as periodic: a gap longer than `gap_factor` x the
topic's median sample spacing is a dropout, so rows inside it are NaN, and
nothing is filled before the first or after the last sample. Rows run from
the latest first sample of any input to the earliest last sample.

There is deliberately no "holds across a silence" mode for topics that only
report on change: on two V25A runs (2026-07-29 and 2026-08-15) every topic
was periodic, with discrete topics repeating their value as a heartbeat.
Add one only if such a topic turns up.
"""

from collections.abc import Collection

import numpy as np
import pandas as pd

from orion_backend.derived_metrics.interpolation import Interp, interp_for

DEFAULT_GAP_FACTOR = 3


def validate_settings(
    inputs: Collection[str], base: str | None, gap_factor: float
) -> None:
    """Raise ValueError for settings `align_inputs` can't work with."""
    if base is not None and base not in inputs:
        raise ValueError(f"base {base!r} is not one of the inputs")
    if gap_factor < 1:
        # Below 1, a topic's normal sample spacing would count as a dropout.
        raise ValueError(f"gap_factor must be at least 1, got {gap_factor}")


def align_inputs(
    inputs: dict[str, pd.DataFrame],
    base: str | None = None,
    gap_factor: float = DEFAULT_GAP_FACTOR,
) -> pd.DataFrame:
    """Align raw topic frames onto shared rows.

    Args:
        inputs: Topic name -> frame indexed by time, one column per position
            in Penelope's `values[]`.
        base: Topic whose timestamps drive the rows. Defaults to the
            most-sampled LINEAR input (first in `inputs` order on a tie).
        gap_factor: What counts as a dropout, in multiples of each topic's
            median sample spacing. At least 1.

    Returns:
        One column per (topic, position), so `aligned[topic]` has the same
        columns as `inputs[topic]`. Empty if any input has no samples or
        the inputs don't overlap in time.
    """
    validate_settings(inputs.keys(), base, gap_factor)

    kinds = {topic: interp_for(topic) for topic in inputs}
    frames = {topic: _clean(df, kinds[topic]) for topic, df in inputs.items()}
    rows = _shared_rows(frames, kinds, base)
    rows_ns = _ns(rows)

    columns = {
        (topic, position): _fill(
            df[position].dropna(), rows_ns, kinds[topic], gap_factor
        )
        for topic, df in frames.items()
        for position in df.columns
    }
    return pd.DataFrame(columns, index=rows)


def _clean(df: pd.DataFrame, kind: Interp) -> pd.DataFrame:
    """Sort by time and collapse duplicate timestamps (common in CAN logs)."""
    if df.empty:
        return df
    df = df.set_axis(pd.DatetimeIndex(df.index).as_unit("ns")).sort_index(kind="stable")
    grouped = df.groupby(level=0, sort=False)
    # Averaging is fine for a measurement but would invent states.
    return grouped.mean() if kind is Interp.LINEAR else grouped.last()


def _shared_rows(
    frames: dict[str, pd.DataFrame], kinds: dict[str, Interp], base: str | None
) -> pd.DatetimeIndex:
    """Base timestamps plus PREVIOUS change times, trimmed to the overlap."""
    if not frames or any(df.empty for df in frames.values()):
        return pd.DatetimeIndex([], tz="UTC").as_unit("ns")

    base = base or _pick_base(frames, kinds)
    rows = frames[base].index
    for topic, df in frames.items():
        if kinds[topic] is Interp.PREVIOUS and topic != base:
            rows = rows.union(_change_times(df))

    start = max(df.index[0] for df in frames.values())
    end = min(df.index[-1] for df in frames.values())
    return pd.DatetimeIndex(rows[(rows >= start) & (rows <= end)])


def _pick_base(frames: dict[str, pd.DataFrame], kinds: dict[str, Interp]) -> str:
    """The most-sampled LINEAR topic, or most-sampled of all if none are.

    PREVIOUS topics are fully captured by their change times, so a
    fast-repeating flag shouldn't dictate the rows. Ties go to the first
    topic in input order.
    """
    linear = [topic for topic in frames if kinds[topic] is Interp.LINEAR]
    return max(linear or frames, key=lambda topic: len(frames[topic]))


def _change_times(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Timestamps where any position differs from the previous sample.

    Two missing values in a row count as unchanged; NaN != NaN would
    otherwise make every null sample a change and add a row for each.
    """
    values = df.to_numpy(dtype=float)
    now, before = values[1:], values[:-1]
    same = (now == before) | (np.isnan(now) & np.isnan(before))
    changed = np.ones(len(df), dtype=bool)
    changed[1:] = ~same.all(axis=1)
    return pd.DatetimeIndex(df.index[changed])


def _fill(
    series: pd.Series, rows_ns: np.ndarray, kind: Interp, gap_factor: float
) -> np.ndarray:
    """One topic position's values at `rows_ns`; NaN where not covered."""
    out = np.full(len(rows_ns), np.nan)
    if series.empty or len(rows_ns) == 0:
        return out

    # Nanoseconds since the first sample: epoch ns (~1.7e18) lose precision
    # when np.interp casts them to float64.
    x = _ns(series.index)
    t = rows_ns - x[0]
    x = x - x[0]
    y = series.to_numpy(dtype=float)

    covered, prev = _covered(x, t, gap_factor)
    if kind is Interp.LINEAR:
        out[covered] = np.interp(t[covered], x, y)
    else:
        out[covered] = y[prev[covered]]
    return out


def _covered(
    x: np.ndarray, t: np.ndarray, gap_factor: float
) -> tuple[np.ndarray, np.ndarray]:
    """Which rows `t` the sorted sample times `x` give a trustworthy value for.

    A row is covered if it lands on a sample, or falls between two samples
    no more than `gap_factor` x the median spacing apart. Rows before the
    first sample, after the last, or inside a dropout are not.

    Args:
        x: Sample times, ascending, in ns since the first sample.
        t: Row times, ascending, on the same scale as `x`.
        gap_factor: Dropout threshold, in multiples of the median spacing.

    Returns:
        (covered, prev): a boolean mask over `t`, and for each row the index
        of the sample at or before it (only meaningful where covered).
    """
    after = np.searchsorted(x, t, side="right")  # x[after - 1] <= t < x[after]
    # Clamped so every row indexes safely; out-of-range rows fail `started`
    # or `after < len(x)` below anyway.
    prev = np.maximum(after - 1, 0)
    nxt = np.minimum(after, len(x) - 1)
    started = after > 0
    max_gap = gap_factor * np.median(np.diff(x)) if len(x) > 1 else 0

    on_sample = started & (x[prev] == t)
    between = started & (after < len(x)) & (x[nxt] - x[prev] <= max_gap)
    return on_sample | between, prev


def _ns(index: pd.Index) -> np.ndarray:
    """Timestamps as int64 nanoseconds since the epoch (UTC)."""
    return (
        pd.DatetimeIndex(index).as_unit("ns").to_numpy("datetime64[ns]").view("int64")
    )
