import type { PipelineRunFilters } from "@schemas/pipeline.schema";
import type { RunListFilters } from "@schemas/run.schema";


export const runKeys = {
  all: ["runs"] as const,
  lists: () => [...runKeys.all, "list"] as const,
  list: (filters: RunListFilters) => [...runKeys.lists(), filters] as const,
  detail: (runId: string | undefined) => [...runKeys.all, "detail", runId] as const,
};

export const penelopeRunKeys = {
  all: ["penelope-runs"] as const,
};

// Penelope's sensor types: fixed reference data.
export const sensorKeys = {
  all: ["sensors"] as const,
};

export const pipelineRunKeys = {
  all: ["pipeline-runs"] as const,
  list: (filters: PipelineRunFilters) => [...pipelineRunKeys.all, "list", filters] as const,
  detail: (jobId: number | undefined) => [...pipelineRunKeys.all, "detail", jobId] as const,
};


export const runDataKeys = {
  root: ["run-data"] as const,
  all: (runId: string | undefined) => [...runDataKeys.root, runId] as const,
  metrics: (runId: string | undefined) => [...runDataKeys.all(runId), "metrics"] as const,
  state: (runId: string | undefined, range: object | undefined) =>
    [...runDataKeys.all(runId), "state", range] as const,
  sensors: (runId: string | undefined, range: object | undefined) =>
    [...runDataKeys.all(runId), "sensors", range] as const,
};
