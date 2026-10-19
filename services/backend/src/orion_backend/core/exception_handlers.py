from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from orion_backend.core.exceptions import (
    DomainError,
    InvalidParameterError,
    NotFoundError,
    ServiceUnavailableError,
    UpstreamError,
)
from orion_backend.schemas.error_schema import ErrorResponse


async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, NotFoundError)
    body = ErrorResponse(
        detail=str(exc), resource_type=exc.resource_type, resource_id=exc.resource_id
    )
    return JSONResponse(status_code=404, content=body.model_dump())


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(status_code=400, content=ErrorResponse(detail=str(exc)).model_dump())
  
  
def _status_handler(
    status_code: int,
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    """A handler that returns `ErrorResponse(detail=str(exc))` with `status_code`."""

    async def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status_code, content=ErrorResponse(detail=str(exc)).model_dump()
        )

    return handler


def register_exception_handlers(app: FastAPI) -> None:
    # Specific handlers first, catch-all last.
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(InvalidParameterError, _status_handler(422))
    app.add_exception_handler(UpstreamError, _status_handler(502))
    app.add_exception_handler(ServiceUnavailableError, _status_handler(503))
    app.add_exception_handler(DomainError, _status_handler(400))
