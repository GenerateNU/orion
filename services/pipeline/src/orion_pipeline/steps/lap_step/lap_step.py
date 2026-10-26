from collections.abc import Iterator
from datetime import datetime

import pandas as pd
from sqlalchemy import select

from orion_core.models import EstimatedCarState
from orion_pipeline.clients.base_client import BaseClient
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.lap_step.lap_utils import (
    Gate,
    RevisitMemory,
    TrackPoint,
    apply_min_lap_time,
    build_gate,
    build_lap_rows,
    downsample,
    find_crossings,
    find_revisit,
    make_lap_row,
    seconds_since,
    to_local_xy,
)
from orion_pipeline.steps.step_registry import register_step


@register_step
class LapStep(PipelineStep):
    """Lap detection step. Splits a run into laps by finding a start/finish gate.
    DB TABLES: FROM Orion[estimated_car_state] -> TO Orion[laps]

    Schema: FROM [time, lattitude, longitude] -> TO [run_id, lap_id, start_time, end_time]

    The run is read twice:
    - Pass 1 (`_find_gate`) finds the first spot the car drives over twice and
      puts a short line across the track there, perpendicular to the car's
      heading: the gate.
    - Pass 2 (`transform`, one page at a time) reads the run again from the
      start and ends a lap every time the car drives forward through the gate.

    See docs/lap_detection.md for the full design.

    Deliberately NOT imported in `steps/__init__.py` yet: registering it would
    make every pipeline job fail, because `state_step` doesn't exist and every
    lap_utils helper is still a stub.
    """

    name = "lap_step"
    # state_step doesn't exist yet.
    depends_on = ("state_step",)
    reads_from = "oriondb"
    output_table = "laps"
    pagination_key = ("time",)

    # Untuned starting guesses. These can and should move to Settings later.
    HITBOX_RADIUS_M = 3.0
    MIN_REVISIT_TIME_S = 5.0
    MIN_REVISIT_DISTANCE_M = 50.0
    PASS1_SAMPLE_EVERY = 5
    MIN_HEADING_SPAN_M = 0.1
    GATE_HALF_WIDTH_M = 5.0
    MIN_LAP_TIME_S = 10.0

    def __init__(self, reader: BaseClient, writer: OrionDBClient):
        super().__init__(reader, writer)
        self._reset_state()

    def _reset_state(self) -> None:
        """Clear the state carried across pages, before a new run."""
        # Pass 1: the run's first point (the x/y origin) and its time bounds.
        self._origin_lat: float | None = None
        self._origin_lon: float | None = None
        self._run_start: datetime | None = None
        self._run_end: datetime | None = None
        # Pass 2.
        self._gate: Gate | None = None
        self._previous: TrackPoint | None = None
        self._lap_id = 1
        self._lap_start: datetime | None = None
        self._last_counted: datetime | None = None

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        stmt = select(
            EstimatedCarState.time,
            EstimatedCarState.lattitude,
            EstimatedCarState.longitude,
        ).where(EstimatedCarState.run_id == ctx.run_id)
        return self.reader.iter_pages(stmt, self.pagination_key)

    def run(self, ctx: RunContext) -> None:
        """Pass 1 finds the gate, then Pass 2 reads the run again and writes its laps."""
        self._reset_state()
        self.prepare(ctx)
        gate = self._find_gate(ctx)
        if self._run_start is None or self._run_end is None:
            return  # empty run: nothing to write
        if gate is None:
            # No revisit anywhere, so the whole run is one lap.
            self.write(make_lap_row(ctx.run_id, 1, self._run_start, self._run_end), ctx)
            return

        self._gate = gate
        self._lap_id = 1
        self._lap_start = self._run_start
        self._previous = None
        self._last_counted = None
        for page in self.extract(ctx):
            if page.empty:
                continue
            rows = self.transform(page, ctx)
            if not rows.empty:
                self.write(rows, ctx)

        # The lap still open when the run ends.
        self.write(
            make_lap_row(ctx.run_id, self._lap_id, self._lap_start, self._run_end), ctx
        )

    def _find_gate(self, ctx: RunContext) -> Gate | None:
        """Pass 1: read pages until the car revisits a spot, and put the gate there.

        Also records the origin and the run's start and end times, which
        Pass 2 needs. If a gate is found, `_run_end` is only the end of the
        pages read so far; Pass 2 moves it to the true end.

        Args:
            ctx: The job being run.

        Returns:
            The gate, or None if the car never revisits a spot.
        """
        memory = RevisitMemory()
        global_index = 0
        for page in self.extract(ctx):
            if page.empty:
                continue
            if self._run_start is None:
                first = page.iloc[0]
                self._origin_lat = float(first["lattitude"])
                self._origin_lon = float(first["longitude"])
                self._run_start = first["time"]
            self._run_end = page["time"].iloc[-1]

            sampled = downsample(page, global_index, self.PASS1_SAMPLE_EVERY)
            global_index += len(page)
            origin_lat, origin_lon = self._origin()
            x, y = to_local_xy(
                sampled["lattitude"], sampled["longitude"], origin_lat, origin_lon
            )
            time_s = seconds_since(sampled["time"], self._run_start)

            revisit = find_revisit(
                x,
                y,
                time_s,
                memory,
                self.HITBOX_RADIUS_M,
                self.MIN_REVISIT_TIME_S,
                self.MIN_REVISIT_DISTANCE_M,
                self.MIN_HEADING_SPAN_M,
            )
            if revisit is not None:
                index, heading = revisit
                return build_gate(
                    memory.x[index], memory.y[index], heading, self.GATE_HALF_WIDTH_M
                )
        return None

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        """Pass 2, one page: find gate crossings and turn them into finished laps.

        Unlike other steps, this reads and updates the carry-over state on
        self (the open lap, the last counted crossing, the previous page's
        last point). It still does no I/O.

        Args:
            df: One page of estimated_car_state, in time order.
            ctx: The job being run.

        Returns:
            One row per lap finished in this page (possibly none).

        Raises:
            RuntimeError: If Pass 1 hasn't found a gate or `run` hasn't
                opened the first lap.
        """
        if self._gate is None or self._lap_start is None:
            raise RuntimeError("transform needs a gate and an open lap; call run()")

        origin_lat, origin_lon = self._origin()
        x, y = to_local_xy(df["lattitude"], df["longitude"], origin_lat, origin_lon)
        crossings = find_crossings(x, y, df["time"], self._gate, self._previous)
        crossings = apply_min_lap_time(
            crossings, self._last_counted, self.MIN_LAP_TIME_S
        )
        rows, self._lap_id, self._lap_start = build_lap_rows(
            ctx.run_id, self._lap_id, self._lap_start, crossings
        )
        if crossings:
            self._last_counted = crossings[-1]

        last_time = df["time"].iloc[-1]
        self._previous = TrackPoint(
            x=float(x.iloc[-1]), y=float(y.iloc[-1]), time=last_time
        )
        self._run_end = last_time
        return rows

    def _origin(self) -> tuple[float, float]:
        """The run's first point (lat, lon), the origin for local x/y.

        Returns:
            (origin latitude, origin longitude), in degrees.

        Raises:
            RuntimeError: If Pass 1 hasn't read the first page yet.
        """
        if self._origin_lat is None or self._origin_lon is None:
            raise RuntimeError("origin is not set; Pass 1 must read the first page")
        return self._origin_lat, self._origin_lon
