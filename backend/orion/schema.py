from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Uuid,
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


# Output of the state estimation (Kalman filter) pipeline, one row per instant
# per run. It's the API's only data source: GET /api/runs lists its runIds, and
# GET /api/runs/{id}/laps/{lap}/positions serves its points to PositionMap.
#
# It already exists in Neon and was created outside this repo, so it's mirrored
# here (camelCase names and all) with only the columns the API reads.
# create_tables() deliberately skips it: create_all would build an incomplete
# copy, without the foreign key to pipeline_runs (an internal table).
#
# runId is the UUID that connects the tables. lapId is nullable: points not
# yet assigned to a lap have none.
estimated_car_state_table = Table(
    "estimated_car_state",
    metadata,
    Column("runId", Uuid, primary_key=True),
    Column("time", DateTime(timezone=True), primary_key=True),
    Column("lapId", Integer, nullable=True),
    Column("latitude", Float, nullable=False),
    Column("longitude", Float, nullable=False),
)


def create_tables(engine: Engine) -> None:
    """Create the tables this repo owns if they don't already exist."""
    metadata.create_all(engine, tables=[data_table], checkfirst=True)