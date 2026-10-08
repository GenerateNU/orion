import logging
from datetime import datetime, timedelta
from importlib import metadata

from sqlalchemy import delete, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from penelope.client import PenelopeClient

from .exceptions import OrionConnectionError, OrionSchemaError
from .schema import cleaned_data_table, sensor_sources_table, sensors_table
from .signals_catalog import SIGNALS

logger = logging.getLogger(__name__)



# CONSTANTS 

#soc_tag
SOC_TAG = "BMS/Pack/SoC"

# 3 seconds added to every GPS timestamp.
GPS_TAG_PREFIX = "TPU/GPS/"
DEFAULT_GPS_LAG_SECONDS = 3.0



# turns the raw Penelope tag into a clean name
TAG_TO_NAME = {s["raw_tag"]: s["name"] for s in SIGNALS}

def ensure_reference_tables(engine: Engine) -> None:
    """Create sensors, sensor_sources and cleaned_data if missing, and fill
    sensors + sensor_sources from the catalog."""
    try:
        metadata.create_all(
            engine,
            tables=[sensors_table, sensor_sources_table, cleaned_data_table],
            checkfirst=True,
        )
        with engine.begin() as conn:
            conn.execute(
                pg_insert(sensors_table).on_conflict_do_nothing(),
                [{"name": s["name"], "unit": s["unit"]} for s in SIGNALS],
            )
            conn.execute(
                pg_insert(sensor_sources_table).on_conflict_do_nothing(),
                [{"sourceDataTypeName": s["raw_tag"], "sensor": s["name"]} for s in SIGNALS],
            )
    # log errors 
    except OperationalError as exc:
        logger.exception("Lost connection while setting up reference tables")
        raise OrionConnectionError("Lost connection to OrionDB while setting up reference tables.") from exc
    except SQLAlchemyError as exc:
        logger.exception("Failed to set up reference tables")
        raise OrionSchemaError("OrionDB rejected the reference table setup.") from exc


def insert_cleaned_data(engine: Engine) -> None:
    """Insert data with mapped sensor names and normalized values into orion's cleaned data table"""



# Normalize SOC values 
def _soc_scale(penelope: PenelopeClient, run_id: str, start: datetime, end:datetime) -> float:
    """Detect whether this run's SoC is 0-1 or 0-100"""
    max_soc = penelope.get_max_first_value(run_id, start, end, SOC_TAG)

    # if there is no row for bms/pack/soc, then return 1 because there is nothing to scale 
    if max_soc is None: 
        logger.info("Run %s has no SoC readings", run_id)
        return 1.0

    # if the bms/pack/soc is less than or equal to 1, that means every value is between 0 and 1 
    if max_soc <= 1.0:
        logger.info("Run %s SoC is 0-1 (max=%s); scaling to 0-100", run_id, max_soc)
        return 100.00

    # otherwise its already between 1-100
    logger.info("Run %s SoC is already 0-100 (max=%s)", run_id, max_soc)
    return 1.0

def _normalize_soc(values: list[float], scale: float) -> list[float]:
    """Apply the multiplier so SoC values are 0-100."""
    return [v * scale for v in values] 


# Needs Investigation Part 

INVESTIGATION_NAMES = frozenset({
    "bms_pack_soc_drift",
    "gps_mode",
    "gps_pps",
    "vcu_home_mode",
    "vcu_nero_index",
    "vcu_state_rejection_error",
    "vcu_tsms",
    "vcu_eth_a_accel",
    "vcu_eth_a_gyro",
})

def _flag_investigation_tags(run_id: str, sensor_names: set[str]) -> set[str]:
    """Log a warning listing which NEEDS INVESTIGATION tags appeared in this run.
    Returns the ones found."""
    found = INVESTIGATION_NAMES & sensor_names
    if found:
        logger.warning(
            "Run %s: ingested tags marked NEEDS INVESTIGATION: %s",
            run_id, ", ".join(sorted(found)),
        )
    return found


def _clean_chunk(chunk, soc_scale: float, gps_lag_seconds: float = DEFAULT_GPS_LAG_SECONDS) -> list[tuple]:
    """Clean one chunk of Penelope rows.
    Rename while still an array, fix SoC, shift GPS timestamps, then split.
    Returns (time, sensor, value) tuples."""
        
    gps_lag = timedelta(seconds= gps_lag_seconds)
    rows = []


    for time, tag, _run_id, values in chunk:
        # 1. map raw tag -> clean name (still an array)
        name = TAG_TO_NAME[tag]


        # 2. fix SoC (still an array)
        if tag == SOC_TAG:
            values = _normalize_soc(values, soc_scale)

        # 3. shift GPS timestamps by the lag
        if tag.startswith(GPS_TAG_PREFIX):
            time = time + gps_lag

        # 4. split at the end
        if len(values) == 1:
            rows.append((time, name, float(values[0])))
        else:
            rows.extend((time, f"{name}_{i}", float(v)) for i, v in enumerate(values))

    return rows




def _delete_existing_rows(conn, run_id: str, start: datetime, end: datetime,
                          gps_lag_seconds: float = DEFAULT_GPS_LAG_SECONDS) -> int:
    
    """Delete this run's cleaned_data rows in [start, end] so a rerun replaces
    them instead of duplicating. The window is widened by the GPS lag, since
    shifted GPS rows can land just outside it. Returns rows deleted."""

    lag = timedelta(seconds=gps_lag_seconds)
    c = cleaned_data_table.c
    result = conn.execute(
        delete(cleaned_data_table).where(
            c.runId == run_id,
            c.time >= start + min(lag, timedelta(0)),
            c.time <= end + max(lag, timedelta(0)),
        )
    )
    logger.info("Run %s: deleted %d existing cleaned_data rows", run_id, result.rowcount)
    return result.rowcount


def insert_cleaned_data(conn, run_id: str, rows: list[tuple]) -> int:
    """Insert one chunk of (time, sensor, value) rows into cleaned_data.
    Returns the number of rows written."""
    if not rows:
        return 0
    conn.execute(
        insert(cleaned_data_table),
        [{"runId": run_id, "time": t, "sensor": s, "value": v} for t, s, v in rows],
    )
    return len(rows)