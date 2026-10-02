from dotenv import load_dotenv

load_dotenv()

from orion.db import get_engine
from orion.exceptions import OrionConfigError
from orion.schema import create_tables

# get_engine checks NEON_DB_URL for blank as well as missing (dotenv sets a key
# even when its value is blank) and pins the psycopg2 driver -- SQLAlchemy 2.1
# would otherwise map Neon's plain postgresql:// URL to psycopg v3, which isn't
# installed.
try:
    engine = get_engine()
except OrionConfigError as exc:
    raise SystemExit(str(exc)) from exc

# create_all(checkfirst=True) only creates tables that are missing. It will
# never ALTER one that already exists, so a schema change made after this has
# run needs the table dropped or a migration written -- re-running is a no-op.
create_tables(engine)
print("tables created")
