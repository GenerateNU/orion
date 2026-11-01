"""Laps for a run, from OrionDB `metrics` (read-only)."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion_backend.core.database import get_orion_db
from orion_core.models.orion import Metrics

router = APIRouter(tags=["metrics"])


@router.get("/runs/{run_id}/metrics", summary="Get laps")
async def get_metrics(
    run_id: str, db: AsyncSession = Depends(get_orion_db)
) -> dict[str, Any]:
    """Every lap for the run, in order. Empty list if it has none."""
    rows = await db.scalars(
        select(Metrics).where(Metrics.run_id == run_id).order_by(Metrics.lap_number)
    )
    return {
        "run_id": run_id,
        "laps": [
            {
                "lap_number": r.lap_number,
                "start_time": r.start_time,
                "end_time": r.end_time,
            }
            for r in rows
        ],
    }
