from dotenv import load_dotenv
load_dotenv()

import os
from sqlalchemy import create_engine
from orion.schema import create_tables

# dotenv sets a key even when its value is blank, so a half-filled .env slips
# past a plain os.environ[...] lookup and fails later inside create_engine with
# an ArgumentError that never names NEON_DB_URL. Check for empty rather than
# missing, the same way PenelopeClient.from_env does.
url = os.environ.get("NEON_DB_URL")
if not url:
    raise SystemExit(
        "NEON_DB_URL is not set. Copy .env.example to .env in the repo root "
        "and paste your Neon connection string into it."
    )

engine = create_engine(url)

# create_all(checkfirst=True) only creates tables that are missing. It will
# never ALTER one that already exists, so a schema change made after this has
# run needs the table dropped or a migration written -- re-running is a no-op.
create_tables(engine)
print("tables created")