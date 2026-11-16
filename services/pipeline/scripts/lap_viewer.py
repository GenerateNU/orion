"""Interactive viewer for checking the lap step's laps against a real run.

Loads a processed run's stored laps (the `laps` table) and estimated positions
(`estimated_car_state`) from OrionDB, reruns gate detection on the positions,
and plots the path with the gate, every gate crossing and the stored lap
boundaries. A slider (and the arrow keys) steps through the points in time
order, so you can see where each lap really starts and ends.

Run from the repo root. The database is ORION_DATABASE_URL (from the
environment or .env), or the local orion-db container if that isn't set:

    uv run python services/pipeline/scripts/lap_viewer.py <run_id> [--every 10]

Keys: left/right step one point, shift+left/right step 50 points.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, KeyEvent
from matplotlib.figure import Figure
from matplotlib.widgets import Slider
from sqlalchemy.exc import OperationalError

from orion_core.db.engines import make_sync_engine
from orion_core.queries.orion_queries import select_estimated_positions, select_laps
from orion_core.settings import Settings, SettingsError, get_settings

# The local orion-db container from docker compose (see .env.example), used
# when ORION_DATABASE_URL isn't set in the environment or .env.
LOCAL_DB_URL = "postgresql://orion:orion@localhost:5434/orion"

# Importing orion_pipeline reads the settings (RunContext's defaults), so the
# database URL has to be settled before the imports below.
try:
    get_settings()
except SettingsError:
    os.environ["ORION_DATABASE_URL"] = LOCAL_DB_URL
    get_settings.cache_clear()

from orion_pipeline.clients.oriondb_client import OrionDBClient  # noqa: E402
from orion_pipeline.steps.lap_step.lap_utils import (  # noqa: E402
    FloatArray,
    Gate,
    apply_min_lap_time,
    find_crossings,
    find_gate,
    to_local_xy,
)

# Gaps between positions longer than this are listed and shaded on the slider.
GAP_S = 1.0
# How far back the highlighted trail behind the current point reaches.
TRAIL_S = 2.0
# The rerun gate is drawn in this color, on top of everything else.
GATE_COLOR = "#ff1493"
GATE_ZORDER = 20
# Most laps listed per column of the stored laps table.
TABLE_ROWS = 20
# Points moved by shift+left/right.
BIG_STEP = 50


@dataclass(frozen=True)
class StoredLap:
    """One row of the `laps` table."""

    lap_id: int
    start_time: datetime
    end_time: datetime

    @property
    def duration_s(self) -> float:
        """The lap's length in seconds."""
        return (self.end_time - self.start_time).total_seconds()


@dataclass(frozen=True)
class RunData:
    """One run's estimated positions and stored laps, as read from OrionDB."""

    positions: pd.DataFrame
    laps: list[StoredLap]


@dataclass(frozen=True)
class Analysis:
    """Everything the viewer draws, at full rate (one entry per position)."""

    times: pd.Series
    time_s: FloatArray
    x: FloatArray
    y: FloatArray
    speed_kmh: FloatArray
    gate: Gate | None
    crossings: np.ndarray
    kept: np.ndarray
    lap_start_s: FloatArray
    lap_end_s: FloatArray


def load_run(client: OrionDBClient, run_id: str) -> RunData:
    """Read the run's positions and stored laps."""
    positions = client.read_frame(select_estimated_positions(run_id))
    rows = client.read_frame(select_laps(run_id))
    laps = [
        StoredLap(
            lap_id=int(lap_id),
            start_time=pd.Timestamp(start).to_pydatetime(),
            end_time=pd.Timestamp(end).to_pydatetime(),
        )
        for lap_id, start, end in zip(
            rows["lap_id"], rows["start_time"], rows["end_time"], strict=True
        )
    ]
    return RunData(positions=positions, laps=laps)


def seconds_since(times: pd.Series, start: datetime) -> FloatArray:
    """Seconds from `start` to each time."""
    return np.asarray((times - start).dt.total_seconds(), dtype=np.float64)


def analyze(run: RunData, settings: Settings) -> Analysis:
    """Rerun gate detection on the positions, the same way the lap step does."""
    times = run.positions["time"]
    start_time: datetime = times.iloc[0]
    time_s = seconds_since(times, start_time)
    x, y = to_local_xy(run.positions["lattitude"], run.positions["longitude"])

    gate = find_gate(
        x,
        y,
        time_s,
        sample_every=settings.lap_gate_search_sample_every,
        hitbox_radius_m=settings.lap_hitbox_radius_m,
        min_revisit_time_s=settings.lap_min_revisit_time_s,
        min_revisit_distance_m=settings.lap_min_revisit_distance_m,
        half_width_m=settings.lap_gate_half_width_m,
    )
    crossings = np.array([], dtype=np.intp)
    kept = np.array([], dtype=bool)
    if gate is not None:
        crossings = find_crossings(x, y, gate)
        crossing_times: list[datetime] = times.iloc[crossings].tolist()
        kept_times = set(
            apply_min_lap_time(start_time, crossing_times, settings.lap_min_lap_time_s)
        )
        kept = np.array([t in kept_times for t in crossing_times], dtype=bool)

    # Speed from the positions themselves, so stops show up without more queries.
    step_m = np.hypot(np.diff(x), np.diff(y))
    step_s = np.diff(time_s)
    speed = np.divide(step_m, step_s, out=np.zeros_like(step_m), where=step_s > 0)
    speed_kmh = np.concatenate(([0.0], speed * 3.6))

    return Analysis(
        times=times,
        time_s=time_s,
        x=x,
        y=y,
        speed_kmh=speed_kmh,
        gate=gate,
        crossings=crossings,
        kept=kept,
        lap_start_s=seconds_since(
            pd.Series([lap.start_time for lap in run.laps]), start_time
        ),
        lap_end_s=seconds_since(
            pd.Series([lap.end_time for lap in run.laps]), start_time
        ),
    )


def gaps(time_s: FloatArray) -> list[tuple[int, float]]:
    """(index of the point after the gap, gap length in seconds) for each long gap."""
    dt = np.diff(time_s)
    return [(int(i) + 1, float(dt[i])) for i in np.flatnonzero(dt > GAP_S)]


def lap_index(a: Analysis, t_s: FloatArray) -> np.ndarray:
    """Index into the stored laps of the lap each time falls in ([start, end))."""
    idx = np.searchsorted(a.lap_start_s, t_s, side="right") - 1
    return np.clip(idx, 0, len(a.lap_start_s) - 1)


def gate_offsets(gate: Gate, x: float, y: float) -> tuple[float, float]:
    """(signed distance ahead of the gate line, distance from the gate center)."""
    dx, dy = x - gate.x, y - gate.y
    return dx * gate.heading_x + dy * gate.heading_y, float(np.hypot(dx, dy))


def fmt_time(t: datetime) -> str:
    """A timestamp as HH:MM:SS.ss."""
    return pd.Timestamp(t).strftime("%H:%M:%S.%f")[:-4]


def print_report(run_id: str, run: RunData, a: Analysis, settings: Settings) -> None:
    """Print the stored laps, the rerun gate and crossings, and data gaps."""
    print(f"Run {run_id}")
    print(
        f"  {len(a.time_s):,} positions, {fmt_time(a.times.iloc[0])} -> "
        f"{fmt_time(a.times.iloc[-1])} ({a.time_s[-1]:.1f} s, "
        f"{len(a.time_s) / max(a.time_s[-1], 1e-9):.1f} Hz average)"
    )

    print("\nStored laps (laps table):")
    print(f"  {'lap':>3}  {'start':>11}  {'end':>11}  {'t0 (s)':>8}  {'dur (s)':>8}")
    for lap, t0 in zip(run.laps, a.lap_start_s, strict=True):
        dur = lap.duration_s
        print(
            f"  {lap.lap_id:>3}  {fmt_time(lap.start_time):>11}  "
            f"{fmt_time(lap.end_time):>11}  {t0:>8.1f}  {dur:>8.1f}"
        )

    print("\nGate (rerun on estimated_car_state):")
    if a.gate is None:
        print("  none found: the car never revisits a spot, so the run is one lap")
    else:
        g = a.gate
        print(
            f"  center ({g.x:.1f}, {g.y:.1f}) m, heading ({g.heading_x:.3f}, "
            f"{g.heading_y:.3f}), half-width {g.half_width_m:.1f} m"
        )
        print(
            f"  {len(a.crossings)} forward crossings, {int(a.kept.sum())} kept "
            f"(min lap time {settings.lap_min_lap_time_s:.0f} s)"
        )
        for i, ok in zip(a.crossings, a.kept, strict=True):
            status = "kept" if ok else "dropped"
            print(
                f"    {fmt_time(a.times.iloc[i])}  t={a.time_s[i]:8.1f} s  "
                f"{a.speed_kmh[i]:5.1f} km/h  {status}"
            )

    # Do the rerun's kept crossings reproduce the stored boundaries?
    stored = {lap.end_time for lap in run.laps[:-1]}
    rerun = set(a.times.iloc[a.crossings[a.kept]].tolist())
    match = "match" if stored == rerun else "DO NOT match (stale laps table?)"
    print(f"\n  Rerun boundaries {match} the stored boundaries.")

    long_gaps = gaps(a.time_s)
    print(f"\nGaps over {GAP_S:.0f} s between positions: {len(long_gaps)}")
    for i, length in long_gaps:
        print(
            f"    at t={a.time_s[i - 1]:8.1f} s ({fmt_time(a.times.iloc[i - 1])}): {length:.1f} s"
        )


def draw_map(ax: Axes, a: Analysis, shown: np.ndarray) -> None:
    """The path colored by stored lap, the gate, crossings and lap boundaries."""
    n_laps = len(a.lap_start_s)
    cmap = plt.get_cmap("tab10" if n_laps <= 10 else "tab20")
    shown_lap = lap_index(a, a.time_s[shown])
    for lap in range(n_laps):
        pts = shown[shown_lap == lap]
        ax.scatter(
            a.x[pts], a.y[pts], s=4, color=cmap(lap % cmap.N), label=f"lap {lap + 1}"
        )

    if a.gate is not None:
        g = a.gate
        px, py = -g.heading_y * g.half_width_m, g.heading_x * g.half_width_m
        # Drawn above everything else (GATE_ZORDER) so it is never hidden.
        ax.plot(
            [g.x - px, g.x + px],
            [g.y - py, g.y + py],
            color=GATE_COLOR,
            lw=5,
            solid_capstyle="round",
            label=f"gate ({2 * g.half_width_m:.0f} m)",
            zorder=GATE_ZORDER,
        )
        ax.annotate(
            "",
            xy=(g.x + g.heading_x * 8, g.y + g.heading_y * 8),
            xytext=(g.x, g.y),
            arrowprops={"arrowstyle": "-|>", "color": GATE_COLOR, "lw": 2.5},
            zorder=GATE_ZORDER,
        )
        ax.annotate(
            "gate",
            (g.x + px, g.y + py),
            xytext=(6, 6),
            textcoords="offset points",
            color=GATE_COLOR,
            fontsize=10,
            fontweight="bold",
            zorder=GATE_ZORDER,
        )
        for kept, color, label in (
            (True, "green", "kept"),
            (False, "orange", "dropped"),
        ):
            idx = a.crossings[a.kept == kept]
            ax.scatter(
                a.x[idx],
                a.y[idx],
                s=220,
                facecolors="none",
                edgecolors=color,
                linewidths=2,
                label=f"crossing ({label})",
                zorder=6,
            )

    end_idx = np.clip(
        np.searchsorted(a.time_s, a.lap_end_s, side="left"), 0, len(a.time_s) - 1
    )
    ax.scatter(a.x[end_idx], a.y[end_idx], marker="X", s=90, color="black", zorder=5)
    for lap, i in enumerate(end_idx):
        ax.annotate(
            f"L{lap + 1} end",
            (a.x[i], a.y[i]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("east (m)")
    ax.set_ylabel("north (m)")
    ax.legend(loc="upper right", fontsize=7)


def laps_table(run: RunData) -> tuple[str, int]:
    """The stored laps as a monospace text block, and the font size to show it at.

    Up to `TABLE_ROWS` laps are listed with start and end times. Longer runs
    drop the start time (it is the previous lap's end) and wrap into columns.
    """
    if len(run.laps) <= TABLE_ROWS:
        lines = ["Stored laps", f"{'lap':>3} {'start':>11} {'end':>11} {'dur s':>7}"]
        lines += [
            f"{lap.lap_id:>3} {fmt_time(lap.start_time):>11} "
            f"{fmt_time(lap.end_time):>11} {lap.duration_s:>7.1f}"
            for lap in run.laps
        ]
        return "\n".join(lines), 9

    rows = [
        f"{lap.lap_id:>3} {fmt_time(lap.end_time):>11} {lap.duration_s:>7.1f}"
        for lap in run.laps
    ]
    header = f"{'lap':>3} {'end':>11} {'dur s':>7}"
    columns = [rows[i : i + TABLE_ROWS] for i in range(0, len(rows), TABLE_ROWS)]
    width = len(header)
    lines = ["Stored laps", "   ".join([header] * len(columns))]
    for r in range(TABLE_ROWS):
        cells = [col[r] if r < len(col) else " " * width for col in columns]
        lines.append("   ".join(cells).rstrip())
    return "\n".join(lines), 7 if len(columns) <= 2 else 6


def build_viewer(run_id: str, run: RunData, a: Analysis, every: int) -> Figure:
    """The interactive figure: map, info panel, laps table and time slider."""
    shown = np.arange(0, len(a.time_s), every)
    if shown[-1] != len(a.time_s) - 1:
        shown = np.append(shown, len(a.time_s) - 1)

    fig = plt.figure(figsize=(15, 9))
    fig.suptitle(f"Run {run_id}", fontsize=11)
    map_ax = fig.add_axes((0.05, 0.16, 0.62, 0.78))
    info_ax = fig.add_axes((0.70, 0.55, 0.28, 0.39))
    table_ax = fig.add_axes((0.70, 0.16, 0.28, 0.37))
    slider_ax = fig.add_axes((0.08, 0.05, 0.84, 0.04))
    for ax in (info_ax, table_ax):
        ax.axis("off")

    draw_map(map_ax, a, shown)
    table, table_font = laps_table(run)
    table_ax.text(0, 1, table, va="top", family="monospace", fontsize=table_font)
    info = info_ax.text(0, 1, "", va="top", family="monospace", fontsize=10)

    (trail,) = map_ax.plot([], [], color="red", lw=2, zorder=6)
    current = map_ax.scatter([], [], s=160, color="red", edgecolors="black", zorder=7)

    slider = Slider(slider_ax, "point", 0, len(shown) - 1, valinit=0, valstep=1)
    # Stored lap boundaries and data gaps, in slider (shown point) units.
    for end_s in a.lap_end_s[:-1]:
        pos = np.searchsorted(a.time_s[shown], end_s)
        slider_ax.axvline(float(pos), color="black", lw=2)
    # The slider steps through points, so a gap is a single step: mark it.
    for i, _length in gaps(a.time_s):
        pos = np.searchsorted(shown, i)
        slider_ax.axvline(float(pos), color="purple", lw=4, alpha=0.6)
    if a.gate is not None:
        for i, ok in zip(a.crossings, a.kept, strict=True):
            pos = np.searchsorted(shown, i)
            slider_ax.axvline(
                float(pos), color="green" if ok else "orange", lw=1, ls="--"
            )

    slider_ax.set_title(
        "black: stored lap ends   green/orange dashed: crossings (kept/dropped)   "
        "purple: data gap",
        fontsize=8,
    )

    def update(value: float) -> None:
        i = int(shown[int(value)])
        t = a.time_s[i]
        current.set_offsets([[a.x[i], a.y[i]]])
        lo = int(np.searchsorted(a.time_s, t - TRAIL_S))
        trail.set_data(a.x[lo : i + 1], a.y[lo : i + 1])

        lap = int(lap_index(a, np.array([t]))[0])
        gap_s = t - a.time_s[i - every] if i >= every else 0.0
        gap_note = f"  ({gap_s:.0f} s gap before)" if gap_s > GAP_S * every else ""
        lines = [
            f"time      {fmt_time(a.times.iloc[i])}",
            f"elapsed   {t:9.2f} s{gap_note}",
            f"point     {i:,} / {len(a.time_s) - 1:,}",
            f"speed     {a.speed_kmh[i]:6.1f} km/h",
            "",
            f"stored lap {lap + 1}",
            f"  into lap {t - a.lap_start_s[lap]:8.2f} s",
            f"  lap ends {a.lap_end_s[lap] - t:8.2f} s from now",
        ]
        if a.gate is not None:
            ahead, dist = gate_offsets(a.gate, a.x[i], a.y[i])
            lines += ["", f"to gate   {dist:7.1f} m", f"ahead     {ahead:7.1f} m"]
        info.set_text("\n".join(lines))
        slider.valtext.set_text(f"{t:.1f} s")
        fig.canvas.draw_idle()

    def on_key(event: Event) -> None:
        if not isinstance(event, KeyEvent) or event.key is None:
            return
        steps = {
            "left": -1,
            "right": 1,
            "shift+left": -BIG_STEP,
            "shift+right": BIG_STEP,
        }
        if event.key in steps:
            value = int(slider.val) + steps[event.key]
            slider.set_val(min(max(value, 0), len(shown) - 1))

    slider.on_changed(update)
    fig.canvas.mpl_connect("key_press_event", on_key)
    update(0)
    # Keep the widgets alive as long as the figure.
    fig._lap_viewer_widgets = (slider, trail, current)  # type: ignore[attr-defined]
    return fig


def main(argv: list[str] | None = None) -> int:
    """Load the run, print the report and open the viewer."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_id")
    parser.add_argument(
        "--every", type=int, default=10, help="plot every Nth point (default 10)"
    )
    parser.add_argument(
        "--save", help="save the figure to this path instead of showing it"
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    engine = make_sync_engine(settings.orion_database_url, read_only=True)
    client = OrionDBClient(engine, settings.pipeline_page_size)
    try:
        run = load_run(client, args.run_id)
    except OperationalError as e:
        print(f"Could not connect to OrionDB: {e.orig}", file=sys.stderr)
        return 1

    missing = [
        name
        for name, empty in (
            ("estimated_car_state", run.positions.empty),
            ("laps", not run.laps),
        )
        if empty
    ]
    if missing:
        print(
            f"No {' or '.join(missing)} rows for run {args.run_id}. "
            f"Run the pipeline first: uv run orion-pipeline run {args.run_id}",
            file=sys.stderr,
        )
        return 1

    analysis = analyze(run, settings)
    print_report(args.run_id, run, analysis, settings)

    # Free the arrow keys from matplotlib's back/forward navigation.
    for keymap in ("keymap.back", "keymap.forward"):
        plt.rcParams[keymap] = [
            k for k in plt.rcParams[keymap] if k not in ("left", "right")
        ]
    fig = build_viewer(args.run_id, run, analysis, max(args.every, 1))
    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f"\nSaved {args.save}")
    else:
        plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
