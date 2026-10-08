import httpx

from orion_core.schemas.pipeline_run_schema import PipelineRunCreate, PipelineRunResponse


class PipelineService:
    """Talks to the pipeline service over HTTP. The backend never runs steps itself."""

    def __init__(self, http: httpx.AsyncClient):
        self.http = http

    async def trigger(self, body: PipelineRunCreate) -> PipelineRunResponse:
        response = await self.http.post("/runs", json=body.model_dump())
        response.raise_for_status()
        return PipelineRunResponse.model_validate(response.json())

    async def get(self, pipeline_run_id: int) -> PipelineRunResponse:
        response = await self.http.get(f"/runs/{pipeline_run_id}")
        response.raise_for_status()
        return PipelineRunResponse.model_validate(response.json())
