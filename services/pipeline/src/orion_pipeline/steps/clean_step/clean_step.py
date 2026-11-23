import logging
from collections.abc import Iterator
from datetime import datetime

import pandas as pd

from orion_core.db.sensor_catalog import lagged_raw_tags
from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.clean_step.clean_utils import (
    correct_gps_time,
    first_values,
    map_sensor_names,
    to_epoch_s,
)
from orion_pipeline.steps.clean_step.gps_lag import (
    LagResult,
    Segment,
    track_gps_lag,
)
from orion_pipeline.steps.clean_step.gps_lag_config import MS_TO_MPH, LagTrackerConfig
from orion_pipeline.steps.step_registry import register_step

logger = logging.getLogger(__name__)

# Reference speed: on the same timeline as the rest of the car data.
VCU_SPEED_TAG = "VCU/CarState/speed"  # mph
# Logged in m/s, whatever the sensor catalog says.
GPS_SPEED_TAG = "TPU/GPS/GroundSpeed"


def estimate_run_gps_lag(readings: pd.DataFrame, cfg: LagTrackerConfig) -> LagResult:
    """Track the GPS delay over a whole run's VCU speed and GroundSpeed readings.
    No I/O, so tests and scripts run exactly this."""
    vcu = readings[readings["raw_tag"] == VCU_SPEED_TAG]
    gps = readings[readings["raw_tag"] == GPS_SPEED_TAG]
    return track_gps_lag(
        to_epoch_s(vcu["time"]),
        first_values(vcu["values"]),
        to_epoch_s(gps["time"]),
        first_values(gps["values"]) * MS_TO_MPH,
        cfg,
    )


def log_gps_lag(run_id: str, result: LagResult) -> None:
    """Log the segment table. Diagnostics only."""
    logger.info(
        "run %s: GPS lag over %d segment(s), scale %.3f",
        run_id,
        len(result.segments),
        result.scale,
    )
    for i, seg in enumerate(result.segments):
        logger.info(
            "  segment %d: %.1f s long, lag %.2f s, %s, %d samples",
            i,
            seg.end_t - seg.start_t,
            seg.lag_s,
            seg.quality,
            seg.n_samples,
        )


@register_step
class CleanStep(PipelineStep):
    """Clean data step. Reads raw data from Penelope cleans then saves to Orion.
    DB TABLES: FROM Penelope[data] -> TO Orion[cleaned_data]

    Schema: FROM [time, raw_tag, values] -> TO [run_id, time, sensor, values]
    """

    name = "clean_step"
    reads_from = "penelope"
    output_table = "cleaned_data"
    pagination_key = ("time", "raw_tag")

    # The reader for the clean step will always be PenelopeClient and never OrionDBClient
    reader: PenelopeClient

    def __init__(self, reader: PenelopeClient, writer: OrionDBClient):
        super().__init__(reader, writer)
        self.sensor_map: dict[str, str] = {}
        self.gps_segments: list[Segment] = []
        # Earliest and latest cleaned reading time across every page written.
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    def prepare(self, ctx: RunContext) -> None:
        # Everything that can fail runs before super().prepare() deletes the run's
        # old output, so a failed re-run leaves the previous cleaned_data in place.
        # sensor_sources lives in OrionDB, so it's read through the writer.
        # TODO: move to the step's own OrionDB access once steps own their DB clients.
        self.sensor_map = self.writer.read_sensor_map()
        if not self.sensor_map:
            raise ValueError("sensor_sources is empty; nothing to clean")
        self.gps_segments = self.estimate_gps_lag(ctx)
        super().prepare(ctx)
        self.start_time = None
        self.end_time = None

    def estimate_gps_lag(self, ctx: RunContext) -> list[Segment]:
        """Track the GPS delay over the WHOLE run, before any page is cleaned.

        Never estimated per page: a page can be all parked or all GPS outage, and
        the delay would change with the page size. `transform` only looks up the
        result.
        """
        readings = self.reader.read_run_readings(
            ctx.run_id, [VCU_SPEED_TAG, GPS_SPEED_TAG]
        )
        cfg = LagTrackerConfig(default_lag_s=ctx.gps_time_offset_s)
        result = estimate_run_gps_lag(readings, cfg)
        log_gps_lag(ctx.run_id, result)
        return result.segments

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        # Only pulls tags we can map, unmapped tags never leave Penelope.
        return self.reader.iter_readings(
            ctx.run_id, self.pagination_key, data_type_names=self.sensor_map.keys()
        )

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        cleaned = map_sensor_names(df, self.sensor_map, ctx.run_id)
        # GPS rows are stamped late: move them back by the run's tracked lag.
        corrected = correct_gps_time(
            cleaned,
            df["raw_tag"].isin(lagged_raw_tags()),
            self.gps_segments,
        )
        # Each segment gets one constant lag, so where a later segment's lag is bigger
        # its rows can move back over the previous segment's, and two rows of one
        # sensor can land on the same corrected time, which cleaned_data's primary
        # key rejects. Only catches duplicates within this page.
        dup = corrected.duplicated(["time", "sensor"])
        if dup.any():
            logger.warning(
                "run %s: dropped %d row(s) with duplicate (time, sensor) after GPS correction",
                ctx.run_id,
                int(dup.sum()),
            )
            corrected = corrected[~dup]
        return corrected

    def write(self, df: pd.DataFrame, ctx: RunContext) -> None:
        """Writes the page and widens the run's time bounds to cover it.

        Bounds come from the cleaned (time-shifted) rows, so they match what
        `cleaned_data` holds. Pages are ordered by raw time, but the GPS shift
        can move rows past a page edge, so every page is checked.
        """
        if not df.empty:
            page_start, page_end = df["time"].min(), df["time"].max()
            if self.start_time is None or page_start < self.start_time:
                self.start_time = page_start
            if self.end_time is None or page_end > self.end_time:
                self.end_time = page_end
        super().write(df, ctx)

    def run(self, ctx: RunContext) -> None:
        """Cleans every page, then records the run's bounds on `runs`.

        A run with no readings gets NULL bounds, clearing any from an earlier run.
        """
        super().run(ctx)
        self.writer.set_run_bounds(ctx.run_id, self.start_time, self.end_time)
