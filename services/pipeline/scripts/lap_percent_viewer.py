"""See whether the lap percentages line up: where is 15% on every lap of a run?

Draws every lap of a run in its own color, plus the run's ideal lap (black)
that the percentages are measured along. A slider picks a lap percentage, and
each lap gets a dot where it reached that percentage, with a black star at the
same percentage on the ideal lap. If the percentages line up, the dots sit
together, across the track from the star. The title gives how far each lap's
dot is from the star.

Reads `lap_progress`, so run the pipeline (or the lap progress step) for the
run first.

Run from the repo root, with a full run id or a unique prefix. The database is
ORION_DATABASE_URL (from the environment or .env), or the local orion-db
container if that isn't set:

    uv run python services/pipeline/scripts/lap_percent_viewer.py 80a58216
    uv run python services/pipeline/scripts/lap_percent_viewer.py 80a58216 --percent 15 --out p15.png

Keys: left/right move 0.5%, shift+left/right move 5%.
"""

import argparse
import os
import sys
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backend_bases import Event, KeyEvent
from matplotlib.widgets import Slider
from numpy.typing import NDArray
from sqlalchemy import select

from orion_core.models.orion import EstimatedCarState, Lap, LapProgress
from orion_core.settings import SettingsError, get_settings

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

from orion_core.db.engines import make_sync_engine  # noqa: E402
from orion_pipeline.clients.oriondb_client import OrionDBClient  # noqa: E402
from orion_pipeline.runner.run_context import RunContext  # noqa: E402
from orion_pipeline.steps.lap_progress_step.ideal_lap import (  # noqa: E402
    choose_laps,
    find_medoid,
    lap_stats,
    laps_from_ids,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (  # noqa: E402
    FloatArray,
    IdealLap,
    resample,
    smooth_loop,
)
from orion_pipeline.steps.lap_step.lap_utils import to_local_xy  # noqa: E402


@dataclass(frozen=True)
class LapPath:
    """One lap's points in local meters, and the percentage at each (NaN where
    the step gave the point none)."""

    lap_id: int
    x: FloatArray
    y: FloatArray
    percent: FloatArray


def find_run_id(client: OrionDBClient, prefix: str) -> str:
    """The one run id in `laps` that starts with `prefix`."""
    stmt = select(Lap.run_id).distinct().where(Lap.run_id.like(f"{prefix}%"))
    matches = client.read_frame(stmt)["run_id"].tolist()
    if len(matches) != 1:
        found = ", ".join(matches) or "none"
        sys.exit(f"Expected one run with laps starting with {prefix!r}, found {found}")
    return str(matches[0])


def where_at(lap: LapPath, percent: float) -> tuple[float, float] | None:
    """Where `lap` was when it first reached `percent`, interpolated between the
    points either side. None if it never got there, or was already past it at
    its first point with a percentage (a lap that started late)."""
    known = ~np.isnan(lap.percent)
    x, y, p = lap.x[known], lap.y[known], lap.percent[known]
    reached = np.flatnonzero(p >= percent)
    if reached.size == 0:
        return None
    i = int(reached[0])
    if i == 0:
        return (float(x[0]), float(y[0])) if p[0] == percent else None
    t = (percent - p[i - 1]) / (p[i] - p[i - 1])
    return float(x[i - 1] + t * (x[i] - x[i - 1])), float(
        y[i - 1] + t * (y[i] - y[i - 1])
    )


def ideal_at(ideal: IdealLap, percent: float) -> tuple[float, float]:
    """The point `percent` of the way round the ideal lap."""
    along = ideal.length_m * percent / 100
    xc, yc = np.append(ideal.x, ideal.x[0]), np.append(ideal.y, ideal.y[0])
    s = np.append(ideal.s, ideal.length_m)
    return float(np.interp(along, s, xc)), float(np.interp(along, s, yc))


def ideal_lap(
    x: FloatArray,
    y: FloatArray,
    times: pd.Series,
    lap_ids: NDArray[np.int64],
    ctx: RunContext,
) -> IdealLap | None:
    """The run's ideal lap, built the way the lap progress step builds it."""
    chosen = choose_laps(
        lap_stats(times, laps_from_ids(times, lap_ids)),
        max_gap_s=ctx.lap_progress_max_gap_s,
        max_lap_time_ratio=ctx.lap_progress_max_lap_time_ratio,
    )
    if not chosen:
        return None
    laps = [
        resample(x[lap_ids == i], y[lap_ids == i], ctx.lap_progress_spacing_m)
        for i in chosen
    ]
    return smooth_loop(
        laps[find_medoid(laps)],
        spacing_m=ctx.lap_progress_spacing_m,
        smoothing_m=ctx.lap_progress_smoothing_m,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_id", help="Run id, or a unique prefix of one.")
    parser.add_argument(
        "--percent", type=float, default=15.0, help="Starting percentage."
    )
    parser.add_argument("--out", help="Save the figure here instead of opening it.")
    args = parser.parse_args()

    settings = get_settings()
    client = OrionDBClient(make_sync_engine(settings.orion_database_url), 100_000)
    run_id = find_run_id(client, args.run_id)
    ctx = RunContext(run_id=run_id)
    points = client.read_frame(
        select(
            EstimatedCarState.time,
            EstimatedCarState.lattitude,
            EstimatedCarState.longitude,
            LapProgress.lap_id,
            LapProgress.lap_percent,
        )
        .join(
            LapProgress,
            (LapProgress.run_id == EstimatedCarState.run_id)
            & (LapProgress.time == EstimatedCarState.time),
        )
        .where(EstimatedCarState.run_id == run_id)
        .order_by(EstimatedCarState.time)
    )
    lap_ids = points["lap_id"].to_numpy(dtype=np.int64)
    x, y = to_local_xy(points["lattitude"], points["longitude"])
    percent = points["lap_percent"].to_numpy(dtype=np.float64)

    laps = [
        LapPath(int(i), x[lap_ids == i], y[lap_ids == i], percent[lap_ids == i])
        for i in np.unique(lap_ids)
        if not np.isnan(percent[lap_ids == i]).all()
    ]
    if not laps:
        sys.exit(f"Run {run_id} has no lap percentages. Run its pipeline first.")
    ideal = ideal_lap(x, y, points["time"], lap_ids, ctx)

    fig, ax = plt.subplots(figsize=(11, 10))
    fig.subplots_adjust(bottom=0.12)
    colors = plt.get_cmap("tab10")
    dots = []
    for k, lap in enumerate(laps):
        color = colors(k % 10)
        ax.plot(lap.x, lap.y, "-", color=color, lw=0.8, alpha=0.35)
        (dot,) = ax.plot(
            [], [], "o", color=color, ms=11, mec="k", label=f"lap {lap.lap_id}"
        )
        dots.append(dot)
    star = None
    if ideal is not None:
        ax.plot(
            np.append(ideal.x, ideal.x[0]), np.append(ideal.y, ideal.y[0]), "k-", lw=1.2
        )
        ax.plot(ideal.x[0], ideal.y[0], "kx", ms=10, mew=2, label="gate (0%)")
        (star,) = ax.plot([], [], "k*", ms=20, label="ideal lap")
    ax.set_aspect("equal")
    ax.set_xlabel("east (m)")
    ax.set_ylabel("north (m)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), borderaxespad=0)

    slider = Slider(
        fig.add_axes((0.12, 0.04, 0.7, 0.03)),
        "% of lap",
        0.0,
        100.0,
        valinit=args.percent,
    )

    def update(value: float) -> None:
        at_star = ideal_at(ideal, value) if ideal is not None else None
        if star is not None and at_star is not None:
            star.set_data([at_star[0]], [at_star[1]])
        gaps: list[str] = []
        for lap, dot in zip(laps, dots, strict=True):
            where = where_at(lap, value)
            if where is None:
                dot.set_data([], [])
                continue
            dot.set_data([where[0]], [where[1]])
            if at_star is not None:
                gap_m = np.hypot(where[0] - at_star[0], where[1] - at_star[1])
                gaps.append(f"{lap.lap_id}: {gap_m:.1f}")
        ax.set_title(
            f"Run {run_id}\n{value:.1f}% of lap. Distance from the ideal lap's point (m), "
            f"by lap:\n{', '.join(gaps) or 'no laps reach this percentage'}",
            fontsize=10,
        )
        fig.canvas.draw_idle()

    def on_key(event: Event) -> None:
        if not isinstance(event, KeyEvent) or event.key is None:
            return
        steps = {"left": -0.5, "right": 0.5, "shift+left": -5.0, "shift+right": 5.0}
        if event.key in steps:
            slider.set_val(float(np.clip(slider.val + steps[event.key], 0, 100)))

    slider.on_changed(update)
    fig.canvas.mpl_connect("key_press_event", on_key)
    update(args.percent)

    if args.out:
        fig.savefig(args.out, dpi=130, bbox_inches="tight")
        print(f"Saved {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
