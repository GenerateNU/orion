from typing import Any

import httpx

from orion_backend.core.exceptions import ConflictError, NotFoundError, UpstreamError
from orion_core.schemas.pipeline_run_schema import PipelineRunCreate, PipelineRunResponse


class PipelineService:
    """Talks to the pipeline service over HTTP. The backend never runs steps itself."""

    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def trigger(self, body: PipelineRunCreate) -> PipelineRunResponse:
        response = await self._request("POST", "/runs", json=body.model_dump())
        return PipelineRunResponse.model_validate(response.json())

    async def list(
        self, run_id: str | None, status: str | None, limit: int
    ) -> list[PipelineRunResponse]:
        params: dict[str, Any] = {"limit": limit}
        if run_id is not None:
            params["run_id"] = run_id
        if status is not None:
            params["status"] = status
        response = await self._request("GET", "/runs", params=params)
        return [PipelineRunResponse.model_validate(job) for job in response.json()]

    async def get(self, pipeline_run_id: int) -> PipelineRunResponse:
        response = await self._request(
            "GET", f"/runs/{pipeline_run_id}", resource_id=pipeline_run_id
        )
        return PipelineRunResponse.model_validate(response.json())

    async def _request(
        self, method: str, url: str, resource_id: object = None, **kwargs: Any
    ) -> httpx.Response:
        """Send a request, turning pipeline API failures into domain errors:
        unreachable -> 502, 404 -> NotFoundError, 409 -> ConflictError, other -> 502."""
        try:
            response = await self.http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise UpstreamError("Pipeline API", exc.__class__.__name__) from exc
        if response.status_code == 404 and resource_id is not None:
            raise NotFoundError("Pipeline job", resource_id)
        if response.status_code == 409:
            raise ConflictError(_detail(response))
        if response.is_error:
            raise UpstreamError("Pipeline API", f"HTTP {response.status_code}")
        return response


def _detail(response: httpx.Response) -> str:
    """The pipeline API's `detail` message, or the raw body if it has none."""
    try:
        return str(response.json()["detail"])
    except (ValueError, KeyError, TypeError):
        return response.text
