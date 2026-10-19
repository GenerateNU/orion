"""Seed `sensors` and `sensor_sources` from `SENSOR_CATALOG`.

Idempotent: rows are upserted, so re-run it after editing the catalog.
Rows no longer in the catalog are kept unless `--prune` is passed.

    uv run python -m orion_core.db.scripts.seed_sensors [--prune]
"""

import argparse
import logging

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from orion_core.db.engines import make_sync_engine
from orion_core.db.sensor_catalog import SENSOR_CATALOG, CatalogEntry
from orion_core.models.orion import Sensors, SensorSources
from orion_core.settings import get_settings

logger = logging.getLogger(__name__)


def _validate(catalog: list[CatalogEntry]) -> None:
    raw_tags = [row["raw_tag"] for row in catalog]
    if len(raw_tags) != len(set(raw_tags)):
        raise ValueError("SENSOR_CATALOG has duplicate raw_tags")

    # Several raw tags may share a sensor, but only if they agree on its unit.
    units: dict[str, str | None] = {}
    for row in catalog:
        sensor, unit = row["sensor"], row["unit"]
        if sensor in units and units[sensor] != unit:
            raise ValueError(f"sensor {sensor!r} has conflicting units")
        units[sensor] = unit


def seed(prune: bool = False) -> None:
    _validate(SENSOR_CATALOG)

    sensors = list(
        {
            row["sensor"]: {"sensor": row["sensor"], "unit": row["unit"]}
            for row in SENSOR_CATALOG
        }.values()
    )
    sources = [
        {"source_data_type_name": row["raw_tag"], "sensor": row["sensor"]}
        for row in SENSOR_CATALOG
    ]

    engine = make_sync_engine(get_settings().orion_database_url)
    # One transaction: sensors first, since sensor_sources references them.
    with engine.begin() as conn:
        stmt = insert(Sensors).values(sensors)
        conn.execute(
            stmt.on_conflict_do_update(
                index_elements=[Sensors.sensor], set_={"unit": stmt.excluded.unit}
            )
        )

        stmt = insert(SensorSources).values(sources)
        conn.execute(
            stmt.on_conflict_do_update(
                index_elements=[SensorSources.source_data_type_name],
                set_={"sensor": stmt.excluded.sensor},
            )
        )

        if prune:
            # Sources before sensors (FK); fails if cleaned_data still uses a sensor.
            raw_tags = [s["source_data_type_name"] for s in sources]
            conn.execute(
                delete(SensorSources).where(
                    SensorSources.source_data_type_name.not_in(raw_tags)
                )
            )
            names = [s["sensor"] for s in sensors]
            conn.execute(delete(Sensors).where(Sensors.sensor.not_in(names)))

    logger.info("seeded %d sensors, %d sensor sources", len(sensors), len(sources))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None
    )
    parser.add_argument(
        "--prune", action="store_true", help="delete rows not in the catalog"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    seed(prune=args.prune)


if __name__ == "__main__":
    main()
