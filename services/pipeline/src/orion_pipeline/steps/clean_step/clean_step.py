from collections.abc import Iterator

import pandas as pd

from orion_pipeline.clients.oriondb_client import OrionDBClient
from orion_pipeline.clients.penelope_client import PenelopeClient
from orion_pipeline.runner.run_context import RunContext
from orion_pipeline.steps.base_step import PipelineStep
from orion_pipeline.steps.clean_step.clean_utils import (
    map_sensor_names,
    shift_sensor_time,
)
from orion_pipeline.steps.step_registry import register_step

GPS_LOCATION_SENSOR = "gps_location"


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

    def prepare(self, ctx: RunContext) -> None:
        super().prepare(ctx)
        # sensor_sources lives in OrionDB, so it's read through the writer.
        # TODO: move to the step's own OrionDB access once steps own their DB clients.
        self.sensor_map = self.writer.read_sensor_map()
        if not self.sensor_map:
            raise ValueError("sensor_sources is empty; nothing to clean")

    def extract(self, ctx: RunContext) -> Iterator[pd.DataFrame]:
        # Only pulls tags we can map, unmapped tags never leave Penelope.
        return self.reader.iter_readings(
            ctx.run_id, self.pagination_key, data_type_names=self.sensor_map.keys()
        )

    def transform(self, df: pd.DataFrame, ctx: RunContext) -> pd.DataFrame:
        cleaned = map_sensor_names(df, self.sensor_map, ctx.run_id)
        # Lag the GPS sensor by offset_time
        return shift_sensor_time(cleaned, GPS_LOCATION_SENSOR, ctx.gps_time_offset_s)
