"""Conventions that keep /docs self-documenting."""

from fastapi.routing import APIRoute

from orion_backend.schemas.error_schema import ErrorResponse

TAGS_METADATA = [
    {"name": "health", "description": "Is the API up?"},
    {"name": "runs", "description": "Runs stored in OrionDB."},
    {"name": "readings", "description": "Raw sensor data from Penelope (read-only)."},
    {"name": "pipeline", "description": "Trigger and inspect pipeline jobs."},
]


def generate_operation_id(route: APIRoute) -> str:
    """`runs-get_run` instead of FastAPI's long default ids."""
    return f"{route.tags[0]}-{route.name}"


def error_responses(*codes: int) -> dict:
    """Document our ErrorResponse on a route: `responses=error_responses(404)`."""
    return {code: {"model": ErrorResponse} for code in codes}
