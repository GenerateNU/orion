from dotenv import load_dotenv
load_dotenv()

import os
from sqlalchemy import create_engine
from orion.schema import create_tables

engine = create_engine(os.environ["NEON_DB_URL"])
create_tables(engine)
print("table created")
