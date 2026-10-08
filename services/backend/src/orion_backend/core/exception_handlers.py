from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from orion_backend.core.exceptions import DomainError, NotFoundError
from orion_backend.schemas.error_schema import ErrorResponse


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    body = ErrorResponse(
        detail=str(exc), resource_type=exc.resource_type, resource_id=exc.resource_id
    )
    return JSONResponse(status_code=404, content=body.model_dump())


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=400, content=ErrorResponse(detail=str(exc)).model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    # Specific handlers first, catch-all last.
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(DomainError, domain_error_handler)
