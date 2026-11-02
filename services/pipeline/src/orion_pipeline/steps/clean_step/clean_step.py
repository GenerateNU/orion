import logging
from collections.abc import Iterator

import numpy as np
import pandas as pd

from orion_core.db.sensor_catalog import lagged_sensors
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
    MS_TO_MPH,
    LagResult,
    LagTrackerConfig,
    Segment,
    SelfCheck,
    self_check,
    track_gps_lag,
)
from orion_pipeline.steps.step_registry import register_step

logger = logging.getLogger(__name__)

# Reference speed: on the same timeline as the rest of the car data.
VCU_SPEED_TAG = "VCU/CarState/speed"  # mph
# Logged in m/s, whatever the sensor catalog says.
GPS_SPEED_TAG = "TPU/GPS/GroundSpeed"
# Written in the same receiver packets, so they share GroundSpeed's lag.
# TPU/GPS/PPS is stamped separately and carries no usable timing, so it's left alone.
GPS_SHIFTED_TAGS = frozenset(
    {GPS_SPEED_TAG, "TPU/GPS/Location", "TPU/GPS/Altitude", "TPU/GPS/Mode"}
)


def estimate_run_gps_lag(
    readings: pd.DataFrame, cfg: LagTrackerConfig
) -> tuple[LagResult, SelfCheck]:
    """Track the GPS delay over a whole run's VCU speed and GroundSpeed readings,
    and self-check the result. No I/O, so tests and scripts run exactly this."""
    vcu = readings[readings["raw_tag"] == VCU_SPEED_TAG]
    gps = readings[readings["raw_tag"] == GPS_SPEED_TAG]
    speeds = (
        to_epoch_s(vcu["time"]),
        first_values(vcu["values"]),
        to_epoch_s(gps["time"]),
        first_values(gps["values"]) * MS_TO_MPH,
    )
    result = track_gps_lag(*speeds, cfg)
    return result, self_check(*speeds, result, cfg)


def log_gps_lag(
    run_id: str,
    readings: pd.DataFrame,
    result: LagResult,
    check: SelfCheck,
    cfg: LagTrackerConfig,
) -> None:
    """Log the segment table and the self-check. Diagnostics only."""
    summary = (
        f"{check.n_windows} usable window(s), {check.agree_frac:.0%} within "
        f"{cfg.check_tolerance_s:.1f} s, worst {check.worst_s:.1f} s"
        if check.n_windows
        else "no usable windows"
    )
    logger.info(
        "run %s: GPS lag over %d segment(s), scale %.3f; self-check: %s",
        run_id,
        len(result.segments),
        result.scale,
        summary,
    )
    if check.suspicious:
        logger.warning(
            "run %s: GPS delay estimate suspicious: %d window(s), %.0f%% within %.1f s, "
            "worst disagreement %.1f s",
            run_id,
            check.n_windows,
            100 * check.agree_frac,
            cfg.check_tolerance_s,
            check.worst_s,
        )
    # Share of GPS gaps that are back-to-back: ~0 when the logger keeps up (1 Hz),
    # ~1 when it is saturated (and the delay is high and wandering).
    gps_t = np.sort(
        to_epoch_s(readings.loc[readings["raw_tag"] == GPS_SPEED_TAG, "time"])
    )
    for i, seg in enumerate(result.segments):
        gaps = np.diff(gps_t[(gps_t >= seg.start_t) & (gps_t <= seg.end_t)])
        back_to_back = (
            float(np.mean(gaps < cfg.back_to_back_s)) if len(gaps) else np.nan
        )
        logger.info(
            "  segment %d: %.1f s long, lag %.2f s [%.2f, %.2f], %s, %d/%d informative, "
            "back_to_back_fraction %.2f",
            i,
            seg.end_t - seg.start_t,
            seg.lag_s,
            seg.ci_lo,
            seg.ci_hi,
            seg.quality,
            seg.n_informative,
            seg.n_samples,
            back_to_back,
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
        result, check = estimate_run_gps_lag(readings, cfg)
        log_gps_lag(ctx.run_id, readings, result, check, cfg)
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
            df["raw_tag"].isin(GPS_SHIFTED_TAGS),
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
