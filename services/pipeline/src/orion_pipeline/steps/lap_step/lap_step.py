from collections.abc import Iterator
from datetime import datetime
from typing import cast

import pandas as pd
from sqlalchemy import func, select

from orion_core.models import EstimatedCarState
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.lap_step.lap_constants import (
    GATE_HALF_WIDTH_M,
    GATE_SEARCH_SAMPLE_EVERY,
    HITBOX_RADIUS_M,
    MIN_HEADING_SPAN_M,
    MIN_LAP_TIME_S,
    MIN_REVISIT_DISTANCE_M,
    MIN_REVISIT_TIME_S,
)
from orion_pipeline.steps.lap_step.lap_utils import (
    Gate,
    TrackPoint,
    VisitedPoints,
    apply_min_lap_time,
    build_gate,
    build_lap_rows,
    downsample,
    find_crossings,
    find_revisit,
    seconds_since,
    to_local_xy,
)
from orion_pipeline.steps.step_registry import register_step


@register_step
class LapStep(PipelineStep):
    name = "lap_step"
    depends_on = ("state_step",)
    reads_from = "oriondb"
    output_table = "laps"
    pagination_key = ("time",)

    # The reader for the lap step will always be OrionDBClient and never PenelopeClient
    reader: OrionDBClient

    # Carried between pages. These are set by `_setup_origin` on the first page.
    _origin_lat: float
    _origin_lon: float
    _start_time: datetime
    _current_lap_id: int
    _current_lap_start: datetime
    # These are set by `_reset_state` and `prepare`.
    _started: bool
    _run_end_time: datetime | None
    _gate: Gate | None
    _visited: VisitedPoints
    _rows_seen: int
    _last_point: TrackPoint | None
    _last_crossing_time: datetime | None

    def prepare(self, ctx: RunContext) -> None:
        super().prepare(ctx)

        self._started = False
        self._run_end_time = None
        self._gate = None
        self._visited = VisitedPoints()
        self._rows_seen = 0
        self._last_point = None
        self._last_crossing_time = None
        ctx.found_gate = False

        find_end_time_stmt = select(func.max(EstimatedCarState.time)).where(
            EstimatedCarState.run_id == ctx.run_id
        )
        # MAX gives one row: the run's last time, or NULL (NaT) for an empty run.
        end_time = self.reader.read_frame(find_end_time_stmt).iloc[0, 0]
        self._run_end_time = None if pd.isna(end_time) else cast(datetime, end_time)

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        stmt = select(
            EstimatedCarState.time,
            EstimatedCarState.lattitude,
            EstimatedCarState.longitude,
        ).where(EstimatedCarState.run_id == ctx.run_id)
        return self.reader.iter_pages(stmt, self.pagination_key)

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """One page: search for the gate until it's found, then count laps.

        Args:
            df: One page of estimated_car_state, in time order.
            ctx: The job being run.

        Returns:
            One row per lap finished in this page (possibly none), including
            the final lap on the run's last page.
        """
        # sets up origin point and start time
        if not self._started:
            self._setup_origin(df)

        # Add X,Y local coordinate columns to our DF
        page = self._add_xy(df)

        # Must find gate before finding crossings
        if not ctx.found_gate:
            self._gate = self._search_for_gate(page)
            ctx.found_gate = self._gate is not None

        # crossings for this page (Empty if no gate)
        crossings = (
            self._find_crossings(page, self._gate) if self._gate is not None else []
        )

        # If this is the last page, the end time is a "crossing" so it can be counted as a lap
        if page["time"].iloc[-1] == self._run_end_time:
            crossings.append(self._run_end_time)  # the run's end closes the final lap

        # Reset the last point of page so it can be transfered to the next page
        self._last_point = self._last_point_of(page)

        # Return the rows to be written to the laps table
        return self._close_laps(crossings, ctx.run_id)

    def _setup_origin(self, df: pd.DataFrame) -> None:
        """Record the origin and start time from the run's first row, and open lap 1."""
        first = df.iloc[0]
        self._origin_lat = float(first["lattitude"])
        self._origin_lon = float(first["longitude"])
        self._start_time = first["time"]
        self._current_lap_id = 1
        self._current_lap_start = self._start_time
        self._started = True

    def _add_xy(self, df: pd.DataFrame) -> pd.DataFrame:
        """The page with local `x` and `y` columns added."""
        x, y = to_local_xy(
            df["lattitude"], df["longitude"], self._origin_lat, self._origin_lon
        )
        return df.assign(x=x, y=y)

    def _search_for_gate(self, page: pd.DataFrame) -> Gate | None:
        """Build the gate at this page's first revisit, or None if it has none."""
        sampled = downsample(page, self._rows_seen, GATE_SEARCH_SAMPLE_EVERY)
        self._rows_seen += len(page)
        time_s = seconds_since(sampled["time"], self._start_time)

        revisit = find_revisit(
            sampled["x"],
            sampled["y"],
            time_s,
            self._visited,
            HITBOX_RADIUS_M,
            MIN_REVISIT_TIME_S,
            MIN_REVISIT_DISTANCE_M,
            MIN_HEADING_SPAN_M,
        )
        if revisit is None:
            return None
        i, heading = revisit
        gate = build_gate(
            float(self._visited.x[i]),
            float(self._visited.y[i]),
            heading,
            GATE_HALF_WIDTH_M,
        )
        self._visited = VisitedPoints()
        return gate

    def _find_crossings(self, page: pd.DataFrame, gate: Gate) -> list[datetime]:
        """This page's gate crossings that pass the minimum lap time."""
        crossings = find_crossings(
            page["x"], page["y"], page["time"], gate, self._last_point
        )
        crossings = apply_min_lap_time(
            crossings, self._last_crossing_time, MIN_LAP_TIME_S
        )
        if crossings:
            self._last_crossing_time = crossings[-1]
        return crossings

    def _last_point_of(self, page: pd.DataFrame) -> TrackPoint:
        """The page's last row, as a TrackPoint."""
        last = page.iloc[-1]
        return TrackPoint(x=float(last["x"]), y=float(last["y"]), time=last["time"])

    def _close_laps(self, crossings: list[datetime], run_id: str) -> pd.DataFrame:
        """Close one lap per crossing, and open the next one."""
        rows, self._current_lap_id, self._current_lap_start = build_lap_rows(
            run_id, self._current_lap_id, self._current_lap_start, crossings
        )
        return rows
