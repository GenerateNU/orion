// Every backend path the frontend calls, relative to the axios baseURL (/api/v1).
const run = (runId: string) => `/runs/${encodeURIComponent(runId)}`;

export const apiUrls = {
  runs: () => "/runs",
  run,
  penelopeRuns: () => "/penelope/runs",
  sensors: () => "/sensors",
  pipelineRuns: () => "/pipeline/runs",
  pipelineRun: (jobId: number) => `/pipeline/runs/${jobId}`,

  // A run's data: raw readings from Penelope, then pipeline stage outputs
  sensorData: (runId: string) => `${run(runId)}/sensors/data`,
  state: (runId: string) => `${run(runId)}/state`,
  metrics: (runId: string) => `${run(runId)}/metrics`, // PLANNED: no backend route yet
};
