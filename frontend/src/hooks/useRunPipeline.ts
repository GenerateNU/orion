import { usePipelineMutations, usePipelineRuns } from "@hooks/usePipelineRuns";
import { isPipelineActive } from "@schemas/pipeline.schema";

// Re-runs the whole pipeline for one run. isBusy is true while the request is in
// flight or a job for the run is queued or running. Polling, and refetching the
// run's data after the job finishes, come from usePipelineRuns.
export const useRunPipeline = (runId: string) => {
  const { pipelineRuns } = usePipelineRuns({ run_id: runId });
  const { triggerPipeline, isTriggeringPipeline } = usePipelineMutations();

  const isBusy =
    isTriggeringPipeline || (pipelineRuns ?? []).some((job) => isPipelineActive(job.status));

  // Errors (e.g. a 409 because a job is already active) aren't shown on the dashboard.
  const runPipeline = () => {
    triggerPipeline({ run_id: runId }).catch(() => undefined);
  };

  return { isBusy, runPipeline };
};
