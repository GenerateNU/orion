import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from orion.repository import DataPointRepository
from orion.signals_catalog import SIGNALS
from penelope.client import PenelopeClient

logger = logging.getLogger(__name__)

# GPS timestamps run 3 s late, so shift them back by 3 s.
GPS_TAG_PREFIX = "TPU/GPS/"
DEFAULT_GPS_LAG_SECONDS = -3.0

# turns the raw Penelope tag into a clean name
TAG_TO_NAME = {s["raw_tag"]: s["name"] for s in SIGNALS}
GPS_NAMES = [name for tag, name in TAG_TO_NAME.items() if tag.startswith(GPS_TAG_PREFIX)]

# clean name -> unit, so suffixed sensors (vcu_eth_a_accel_0) can get their base sensor's unit
NAME_TO_UNIT = {s["name"]: s.get("unit") for s in SIGNALS}

class CleanService:
    def __init__(self, penelope_client: PenelopeClient, orion_client: DataPointRepository) -> None:
        self.penelope_client = penelope_client
        self.orion_client = orion_client

    def _clean_chunk(self, chunk, gps_lag_seconds: float = DEFAULT_GPS_LAG_SECONDS) -> pd.DataFrame:
        """Clean one chunk of Penelope rows. Rename, shift GPS timestamps, then split.
        Returns (time, sensor, value) tuples."""
            
        gps_lag = timedelta(seconds= gps_lag_seconds)
        cleaned_rows = []

        for time, tag, run_id, values in chunk:
            # 1. map raw tag -> clean name (still an array)
            name = TAG_TO_NAME[tag]

            # 2. shift GPS timestamps by the lag
            if tag.startswith(GPS_TAG_PREFIX):
                time = time + gps_lag

            cleaned_rows.append((time, name, run_id, [float(v) for v in values]))

        return pd.DataFrame(cleaned_rows, columns=["time", "sensor", "runId", "value"])

    def clean_data(self, run_id: str, start: datetime, end: datetime, raw_tags: list[str] | None = None) -> pd.DataFrame:
        raw_tags = raw_tags or list(TAG_TO_NAME)
        repo = self.orion_client
        frames = []
        sensors = np.array(list(NAME_TO_UNIT.items()), dtype=object)
        sources = np.array(list(TAG_TO_NAME.items()), dtype=object)
   
        repo.write_sensors(sensors)
        repo.write_sensor_sources(sources)

        raw_rows = self.penelope_client.get_by_run_id_and_time(run_id, start, end, raw_tags)
        for chunk in raw_rows:
            cleaned_chunk = self._clean_chunk(chunk)
            rows = cleaned_chunk[["runId", "time", "sensor", "value"]].to_numpy(dtype=object)
            written = repo.write_cleaned(rows)
            if written:
                frames.append(cleaned_chunk)
        
        return pd.concat(frames, ignore_index=True)

