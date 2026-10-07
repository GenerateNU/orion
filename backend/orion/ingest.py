import logging
from importlib import metadata

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .exceptions import OrionConnectionError, OrionSchemaError
from .schema import cleaned_data_table, metadata, sensor_sources_table, sensors_table
from .signals_catalog import SIGNALS

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