import logging
from importlib import metadata

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .exceptions import OrionConnectionError, OrionSchemaError
from .schema import cleaned_data_table, metadata, sensor_sources_table, sensors_table
from .signals_catalog import SIGNALS
from penelope.client import PenelopeClient 

logger = logging.getLogger(__name__)

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


import logging
from datetime import datetime

from penelope.client import PenelopeClient

logger = logging.getLogger(__name__)

SOC_TAG = "BMS/Pack/SoC"


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


