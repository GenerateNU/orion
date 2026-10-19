// Every backend path the frontend calls, relative to the axios baseURL (/api/v1).
const run = (runId: string) => `/runs/${encodeURIComponent(runId)}`;

export const apiUrls = {
  runs: () => "/runs",
  run,
  penelopeRuns: () => "/penelope/runs",
  pipelineRuns: () => "/pipeline/runs",
  pipelineRun: (jobId: number) => `/pipeline/runs/${jobId}`,

  // Pipeline stage outputs
  cleanedData: (runId: string) => `${run(runId)}/cleaned`, // PLANNED: no backend route yet
  state: (runId: string) => `${run(runId)}/state`,
  metrics: (runId: string) => `${run(runId)}/metrics`, // PLANNED: no backend route yet
};
