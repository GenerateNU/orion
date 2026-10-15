"""Runs state estimation over cleaned_data for one run and time window."""

import os
from datetime import UTC, datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from orion.repository import DataPointRepository
from services.state_estimation_service import StateEstimationService

RUN_ID = "3adaad41-0f1a-42e3-b6d7-02db50a6644a"
# GPS timestamps are shifted 3 s earlier during cleaning, so start a little before 20:10
START = datetime(2026, 8, 15, 20, 9, 50, tzinfo=UTC)
END = datetime(2026, 8, 15, 20, 13, tzinfo=UTC)


def main() -> None:
    load_dotenv()

    url = os.environ.get("NEON_DB_URL")
    if not url:
        raise SystemExit("NEON_DB_URL is not set. Add NeonDB url to .env.")
    engine = create_engine(url)
    print(f"Writing to {engine.url.host}/{engine.url.database}")

    # estimated_car_state.runId must exist in pipeline_runs
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO pipeline_runs ("runId", stage, "raceDate")
                    VALUES (:run_id, 'cleaned', :race_date) ON CONFLICT ("runId") DO NOTHING"""),
            {"run_id": RUN_ID, "race_date": START.date()},
        )
        # Clear this run's previous estimates in the window so re-running replaces them instead of hitting duplicate keys
        deleted = conn.execute(
            text("""DELETE FROM estimated_car_state
                    WHERE "runId" = :run_id AND time >= :start AND time < :end"""),
            {"run_id": RUN_ID, "start": START, "end": END},
        ).rowcount
    print(f"Deleted {deleted} existing rows from estimated_car_state")

    service = StateEstimationService(DataPointRepository(engine))
    estimated, _ = service.estimate_state(pd.Timestamp(START), pd.Timestamp(END))

    with engine.begin() as conn:
        conn.execute(
            text("""UPDATE pipeline_runs SET stage = 'estimated', "updatedAt" = now() WHERE "runId" = :run_id"""),
            {"run_id": RUN_ID},
        )

    print(estimated.head(10).to_string())
    print(f"{len(estimated)} rows written to estimated_car_state")


if __name__ == "__main__":
    main()
