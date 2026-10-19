from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Liveness check")
async def get_health() -> dict[str, str]:
    """Returns `{"status": "ok"}` if the API process is up."""
    return {"status": "ok"}
