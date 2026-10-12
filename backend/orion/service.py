import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from penelope.client import PenelopeClient
from .repository import DataPointRepository
from .signals_catalog import SIGNALS

logger = logging.getLogger(__name__)

#soc_tag
SOC_TAG = "BMS/Pack/SoC"

# GPS timestamps run 3 s late, so shift them back by 3 s.
GPS_TAG_PREFIX = "TPU/GPS/"
DEFAULT_GPS_LAG_SECONDS = -3.0

# turns the raw Penelope tag into a clean name
TAG_TO_NAME = {s["raw_tag"]: s["name"] for s in SIGNALS}
GPS_NAMES = [name for tag, name in TAG_TO_NAME.items() if tag.startswith(GPS_TAG_PREFIX)]

# clean name -> unit, so suffixed sensors (vcu_eth_a_accel_0) can get their base sensor's unit
NAME_TO_UNIT = {s["name"]: s.get("unit") for s in SIGNALS}

# Needs Investigation rows
INVESTIGATION_NAMES = frozenset(
    s["name"] for s in SIGNALS
    if "NEEDS INVESTIGATION" in (s.get("description") or "").upper()
)

class OrionService:
    def __init__(self, penelope_client: PenelopeClient, orion_client: DataPointRepository):
        self.penelope_client = penelope_client
        self.orion_client = orion_client

    def _flag_investigation_tags(self, run_id: str, sensor_names: set[str]) -> set[str]:
        """Log a warning listing which NEEDS INVESTIGATION tags appeared in this run.
        Returns the ones found."""
        found = INVESTIGATION_NAMES & sensor_names
        if found:
            logger.warning(
                "Run %s: ingested tags marked NEEDS INVESTIGATION: %s",
                run_id, ", ".join(sorted(found)),
            )
        return found

    def _clean_chunk(self, chunk, gps_lag_seconds: float = DEFAULT_GPS_LAG_SECONDS) -> list[tuple]:
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

            # 3. split multivalue sensors 
            if len(values) == 1:
                cleaned_rows.append((time, name, run_id, float(values[0])))
            else:
                cleaned_rows.extend((time, f"{name}_{i}", run_id, float(v)) for i, v in enumerate(values))

        return pd.DataFrame(cleaned_rows, columns=["time", "sensor", "runId", "value"])

    def clean_data(self, run_id: str, start: datetime, end: datetime, raw_tags: list[str] = list(TAG_TO_NAME)):
        repo = self.orion_client
        frames = []
        flagged = set()
        cleaned_rows = []
        sensors = np.array(list(NAME_TO_UNIT.items()), dtype=object)
        sources = np.array(list(TAG_TO_NAME.items()), dtype=object)
        known = set(TAG_TO_NAME.values())
   
        with repo.begin() as conn:
            repo.write_sensors(sensors, conn)
            repo.write_sensor_sources(sources, conn)

            raw_rows = self.penelope_client.get_by_run_id_and_time(run_id, start, end, raw_tags)
            for chunk in raw_rows:
                    # Flag NEEDS INVESTIGATION tags once per run. 
                    names = {TAG_TO_NAME.get(row[1]) for row in chunk}
                    flagged |= self._flag_investigation_tags(run_id, names - flagged)

                    # cleans chunk
                    cleaned_chunk = self._clean_chunk(chunk)

                    # add multivariable sensor names to sensors table
                    new = set(cleaned_chunk["sensor"]) - known
                    repo.write_sensors(
                        np.array([(n, NAME_TO_UNIT.get(n.rsplit("_", 1)[0])) for n in new], dtype=object),
                        conn,
                    )
                    known |= new

                    rows = cleaned_chunk[["runId", "time", "sensor", "value"]].to_numpy(dtype=object)
                    written = repo.write_cleaned(rows, conn)
                    if written:
                        frames.append(cleaned_chunk)
        
        return pd.concat(frames, ignore_index=True)

