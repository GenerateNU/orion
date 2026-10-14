
"""Runs the Penelope -> Orion ingest for one run and time window."""
 
import logging
import os
from datetime import UTC, datetime
 
from dotenv import load_dotenv
from sqlalchemy import create_engine
 
from orion.repository import DataPointRepository
from services.clean_service import CleanService
from penelope.client import PenelopeClient
 
RUN_ID = "5eee6c81-e84d-4f08-b8c4-bc1a481a5ad6"
START = datetime(2026, 8, 15, 18, 17, tzinfo=UTC)
END = datetime(2026, 8, 15, 18, 19, tzinfo=UTC)

def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
 
    url = os.environ.get("NEON_DB_URL")
    if not url:
        raise SystemExit("NEON_DB_URL is not set. Add NeonDB url to .env.")
    engine = create_engine(url)
    print(f"Writing to {engine.url.host}/{engine.url.database}")
 
    service = CleanService(PenelopeClient.from_env(), DataPointRepository(engine))
    df = service.clean_data(RUN_ID, START, END)
 
    print(df.head(10).to_string())
    print(f"{len(df)} rows across {df['sensor'].nunique()} sensors")
 
 
if __name__ == "__main__":
    main()