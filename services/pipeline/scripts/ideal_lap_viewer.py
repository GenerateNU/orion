"""Plot a run's lap points against candidate ideal laps, side by side.

The lap progress step measures every lap along one ideal lap. This draws the
candidates that were compared for it (docs/lap_progress.md):

- median: the chosen lap with the median lap time (the original rule),
- medoid: the chosen lap the others are closest to,
- smoothed: the medoid through a periodic smoothing spline (`--smoothing-m`),
  what the step uses; drawn over the unsmoothed medoid (dashed red) so the
  change shows when zoomed,
- average: the medoid refined by 3 rounds of binned averaging (evaluated and
  rejected; its code lives only in this script now).

Each panel shows the chosen laps' points colored by lap, the other laps' points
in gray, and the candidate as a black line with the gate and 10% marks. The
title gives its length, the average distance from the chosen laps' points to
it, and the share of moving points in the chosen laps that match it. All
panels zoom and pan together.

Run from the repo root, with a full run id or a unique prefix. The database is
ORION_DATABASE_URL (from the environment or .env), or the local orion-db
container if that isn't set:

    uv run python services/pipeline/scripts/ideal_lap_viewer.py 80a58216
    uv run python services/pipeline/scripts/ideal_lap_viewer.py 80a58216 --out laps.png
    uv run python services/pipeline/scripts/ideal_lap_viewer.py 212c3dc4 --show medoid smoothed
"""

import argparse
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from sqlalchemy import select

from orion_core.models.orion import Lap
from orion_core.queries.orion_queries import select_estimated_positions, select_laps
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
    assign_lap_ids,
    choose_laps,
    find_medoid,
    lap_stats,
    laps_from_ids,
)
from orion_pipeline.steps.lap_progress_step.lap_progress_utils import (  # noqa: E402
    FloatArray,
    IdealLap,
    match_to_ideal_lap,
    mean_distance,
    resample,
    smooth_loop,
)
from orion_pipeline.steps.lap_step.lap_utils import (  # noqa: E402
    headings,
    to_local_xy,
)

# The averaging that was evaluated in Stage 3, with the values it used.
AVERAGE_ROUNDS = 3
BIN_M = 1.0
AVERAGE_SMOOTHING_M = 0.25
CANDIDATES = ("median", "medoid", "smoothed", "average")


def find_run_id(client: OrionDBClient, prefix: str) -> str:
    """The one run id in `laps` that starts with `prefix`."""
    stmt = select(Lap.run_id).distinct().where(Lap.run_id.like(f"{prefix}%"))
    matches = client.read_frame(stmt)["run_id"].tolist()
    if len(matches) != 1:
        found = ", ".join(matches) or "none"
        sys.exit(f"Expected one run with laps starting with {prefix!r}, found {found}")
    return str(matches[0])


def match(ruler: IdealLap, x: FloatArray, y: FloatArray, ctx: RunContext) -> FloatArray:
    """Meters along `ruler` for each point, NaN where it doesn't match."""
    hx, hy = headings(x, y)
    return match_to_ideal_lap(
        x,
        y,
        hx,
        hy,
        np.hypot(hx, hy) > 0,
        ruler,
        max_offtrack_m=ctx.lap_progress_max_offtrack_m,
        min_heading_dot=float(
            np.cos(np.radians(ctx.lap_progress_max_heading_diff_deg))
        ),
        heading_weight_m=ctx.lap_progress_heading_weight_m,
    )


def average(laps: list[IdealLap], ruler: IdealLap, ctx: RunContext) -> IdealLap:
    """`AVERAGE_ROUNDS` rounds of: match every lap point to the ruler, average
    the points in each `BIN_M` bin along it, and smooth the averages into the
    next ruler."""
    x = np.concatenate([lap.x for lap in laps])
    y = np.concatenate([lap.y for lap in laps])
    for _ in range(AVERAGE_ROUNDS):
        s = np.concatenate([match(ruler, lap.x, lap.y, ctx) for lap in laps])
        matched = ~np.isnan(s)
        bins = (s[matched] // BIN_M).astype(np.int64)
        count = np.bincount(bins)
        full = count > 0
        mean_x = np.bincount(bins, weights=x[matched])[full] / count[full]
        mean_y = np.bincount(bins, weights=y[matched])[full] / count[full]
        ruler = smooth_loop(
            IdealLap(mean_x, mean_y, np.zeros(len(mean_x)), 0.0),
            spacing_m=ctx.lap_progress_spacing_m,
            smoothing_m=AVERAGE_SMOOTHING_M,
        )
    return ruler


def lap_color(k: int) -> tuple[float, float, float, float]:
    """The color of the `k`th chosen lap."""
    return plt.get_cmap("tab20")(k % 20)


def legend_handles(chosen: list[int]) -> list[Line2D]:
    """Legend entries: the ideal lap, the gate, other laps, then each chosen lap."""

    def dot(color: str | tuple[float, float, float, float], label: str) -> Line2D:
        return Line2D([], [], ls="", marker="o", ms=6, color=color, label=label)

    return [
        Line2D([], [], color="k", lw=1.5, label="candidate ideal lap"),
        Line2D([], [], ls="", marker="*", ms=12, color="r", label="gate (0%)"),
        Line2D([], [], color="r", ls="--", lw=1, label="unsmoothed medoid"),
        dot("0.8", "other laps"),
        *(dot(lap_color(k), f"lap {lap_id}") for k, lap_id in enumerate(chosen)),
    ]


def draw(
    ax: Axes,
    name: str,
    ruler: IdealLap,
    points: pd.DataFrame,
    chosen: list[int],
    ctx: RunContext,
    under: IdealLap | None = None,
) -> None:
    """One panel: the lap points, then `under` (dashed, if given), then the
    candidate on top."""
    other = points[~points["lap_id"].isin(chosen)]
    ax.scatter(other["x"], other["y"], s=1, c="0.8", label="other laps")
    for k, lap_id in enumerate(chosen):
        lap = points[points["lap_id"] == lap_id]
        ax.scatter(lap["x"], lap["y"], s=1, color=lap_color(k), alpha=0.5)

    if under is not None:
        ax.plot(
            np.append(under.x, under.x[0]),
            np.append(under.y, under.y[0]),
            "r--",
            lw=1,
        )
    ax.plot(
        np.append(ruler.x, ruler.x[0]), np.append(ruler.y, ruler.y[0]), "k-", lw=1.5
    )
    ax.plot(ruler.x[0], ruler.y[0], "r*", ms=14)
    for percent in range(10, 100, 10):
        i = int(np.searchsorted(ruler.s, ruler.length_m * percent / 100))
        ax.annotate(
            f"{percent}%",
            (ruler.x[i], ruler.y[i]),
            fontsize=8,
            ha="center",
            bbox={"boxstyle": "round", "fc": "white", "ec": "0.5", "alpha": 0.8},
        )

    lap_points = points[points["lap_id"].isin(chosen)]
    x = lap_points["x"].to_numpy()
    y = lap_points["y"].to_numpy()
    moving = lap_points["moving"].to_numpy()
    matched = np.mean(~np.isnan(match(ruler, x, y, ctx)[moving]))
    ax.set_title(
        f"{name}\nlength {ruler.length_m:.0f} m, "
        f"{mean_distance(ruler, x, y):.2f} m from laps, {matched:.1%} matched"
    )
    ax.set_aspect("equal")
    ax.set_xlabel("east (m)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run_id", help="Run id, or a unique prefix of one.")
    parser.add_argument("--out", help="Save the figure here instead of opening it.")
    parser.add_argument(
        "--show",
        nargs="+",
        choices=CANDIDATES,
        default=list(CANDIDATES),
        help="Which candidates to draw, in order (default: all four).",
    )
    parser.add_argument(
        "--smoothing-m",
        type=float,
        default=get_settings().lap_progress_smoothing_m,
        help="RMS distance the smoothed medoid may stray from it, in meters.",
    )
    args = parser.parse_args()

    settings = get_settings()
    client = OrionDBClient(make_sync_engine(settings.orion_database_url), 100_000)
    run_id = find_run_id(client, args.run_id)
    ctx = RunContext(run_id=run_id)
    positions = client.read_frame(select_estimated_positions(run_id))
    times = positions["time"]
    lap_ids = assign_lap_ids(times, client.read_frame(select_laps(run_id)))
    x, y = to_local_xy(positions["lattitude"], positions["longitude"])

    stats = lap_stats(times, laps_from_ids(times, lap_ids))
    chosen = choose_laps(
        stats,
        max_gap_s=ctx.lap_progress_max_gap_s,
        max_lap_time_ratio=ctx.lap_progress_max_lap_time_ratio,
    )
    if not chosen:
        sys.exit(f"Run {run_id} has no lap that qualifies (it needs 3 or more laps).")

    laps = [
        resample(x[lap_ids == i], y[lap_ids == i], ctx.lap_progress_spacing_m)
        for i in chosen
    ]
    durations = stats.set_index("lap_id").loc[chosen, "duration_s"]
    median_lap = int(durations.sort_values(kind="stable").index[(len(chosen) - 1) // 2])
    medoid_index = find_medoid(laps)
    medoid = laps[medoid_index]

    def build(key: str) -> tuple[str, IdealLap]:
        if key == "median":
            return f"median lap (lap {median_lap})", laps[chosen.index(median_lap)]
        if key == "medoid":
            return f"medoid (lap {chosen[medoid_index]})", medoid
        if key == "smoothed":
            spacing_m, smoothing_m = ctx.lap_progress_spacing_m, args.smoothing_m
            return (
                f"smoothed medoid ({smoothing_m} m)",
                smooth_loop(medoid, spacing_m=spacing_m, smoothing_m=smoothing_m),
            )
        return "average (rejected)", average(laps, medoid, ctx)

    candidates = [(key, *build(key)) for key in args.show]

    time_s = np.asarray((times - times.iloc[0]).dt.total_seconds(), np.float64)
    speed = np.hypot(np.gradient(x), np.gradient(y)) / np.gradient(time_s)
    points = pd.DataFrame(
        {
            "x": x,
            "y": y,
            "lap_id": lap_ids,
            "moving": speed >= ctx.lap_progress_min_speed_mps,
        }
    )

    rows = 1 if len(candidates) <= 3 else 2
    cols = math.ceil(len(candidates) / rows)
    fig, axes = plt.subplots(
        rows,
        cols,
        figsize=(7 * cols, 7.5 * rows),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    for ax, (key, name, ruler) in zip(axes.flat, candidates, strict=False):
        under = medoid if key == "smoothed" else None
        draw(ax, name, ruler, points, chosen, ctx, under)
        ax.set_ylabel("north (m)")
    for ax in axes.flat[len(candidates) :]:
        ax.set_visible(False)
    fig.suptitle(
        f"Run {run_id}: {len(stats)} laps, ideal lap picked from laps {chosen}"
    )
    fig.legend(
        handles=legend_handles(chosen),
        loc="lower center",
        ncol=min(len(chosen) + 3, 12),
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.06 * (1 + len(chosen) // 10) / rows, 1, 1))
    if args.out:
        fig.savefig(args.out, dpi=150)
        print(f"Saved {args.out}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
