from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION
from sqlalchemy.engine import Engine

metadata = MetaData()

# The natural key is (time, dataTypeName, runId): one reading per data type per
# timestamp per run. Penelope's own data bears this out -- three identical pulls
# of the same window produced exactly 3x the distinct triples, so the triple
# never repeats within a pull. `values` being an array is the other tell, since
# several readings at one instant are packed into it rather than split across
# rows.
#
# Declaring it as the primary key is what makes re-ingest idempotent: the
# repository can insert ON CONFLICT DO NOTHING instead of duplicating a window
# every time it is pulled again.
#
# Column order sets the index order. `time` leads because ingest is time-bounded
# (PenelopeClient.get_by_time_bounds) and reads are expected to be too. The
# tradeoff is that filtering on dataTypeName or runId alone cannot use this
# index; add a separate one if that becomes a common query.
data_table = Table(
    "data",
    metadata,
    Column("time", DateTime(timezone=True), primary_key=True),
    Column("dataTypeName", String, primary_key=True),
    Column("runId", String, primary_key=True),
    Column("values", ARRAY(DOUBLE_PRECISION), nullable=False),
)


# One row per race/session -- what GET /api/races serves. Column names match
# the frontend's contract (RaceListView reads race_id, name, dates), so rows
# can be returned as-is.
#
# run_id links a race back to its readings in `data` (Penelope's runId). It is
# nullable so a race can be entered before its data has been ingested.
#
# DRAFT: columns beyond what the frontend reads are still to be agreed.
races_table = Table(
    "races",
    metadata,
    Column("race_id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String, unique=True, nullable=True),
    Column("name", String, nullable=False),
    Column("dates", Date, nullable=True),
)


# Estimated positions from the state estimation (Kalman filter) pipeline --
# what GET /api/races/{id}/laps/{lap}/positions serves to PositionMap.
# Fields match the stub the frontend was built against.
#
# race_id and lap_number come first on purpose: the primary key (and its index)
# follows column order, and the positions query filters on these two.
estimated_positions_table = Table(
    "estimated_positions",
    metadata,
    Column("race_id", Integer, ForeignKey("races.race_id"), primary_key=True),
    Column("lap_number", Integer, primary_key=True),
    # Seconds since the start of the lap, a plain number like the stub's 0.0, 0.1
    Column("timestamp", Float, primary_key=True),
    Column("latitude", Float, nullable=False),
    Column("longitude", Float, nullable=False),
    Column("orientation", Float, nullable=False),
    Column("speed", Float, nullable=False),
    Column("tangential_acceleration", Float, nullable=False),
    Column("centripetal_acceleration", Float, nullable=False),
)


def create_tables(engine: Engine) -> None:
    """Create all tables in this module if they don't already exist."""
    metadata.create_all(engine, checkfirst=True)