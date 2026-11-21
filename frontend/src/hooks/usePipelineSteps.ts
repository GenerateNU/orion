import { useMemo, useState } from "react";
import { usePipelineMutations, usePipelineRuns } from "@hooks/usePipelineRuns";
import {
  PIPELINE_STEPS,
  isPipelineActive,
  type PipelineRunResponse,
  type PipelineStep,
} from "@schemas/pipeline.schema";

export type StepStatus = "idle" | "running" | "succeeded" | "failed";

export type StepState = {
  step: PipelineStep;
  status: StepStatus;
  // When the step's latest job was queued (jobs don't record a finish time).
  lastRunAt: string | undefined;
  error: string | null;
};

// A job runs its start step and every step after it; a whole-pipeline job (step null) runs them all.
const ranStep = (job: PipelineRunResponse, step: PipelineStep) =>
  job.step === null || PIPELINE_STEPS.indexOf(step) >= PIPELINE_STEPS.indexOf(job.step);

// Per-step pipeline status for one run, and an action to re-run the whole pipeline.
// Polling and refetching the run's data after a job finishes come from usePipelineRuns.
export const usePipelineSteps = (runId: string) => {
  const { pipelineRuns } = usePipelineRuns({ run_id: runId });
  const { triggerPipeline, isTriggeringPipeline } = usePipelineMutations();
  const [error, setError] = useState<unknown>(null);

  const steps = useMemo(
    (): StepState[] =>
      PIPELINE_STEPS.map((step) => {
        // Jobs are newest first, so find() gives the step's latest job.
        const job = pipelineRuns?.find((j) => ranStep(j, step));
        return {
          step,
          status: !job ? "idle" : job.status === "queued" ? "running" : job.status,
          lastRunAt: job?.queued_at,
          error: job?.status === "failed" ? job.error : null,
        };
      }),
    [pipelineRuns],
  );

  const isBusy =
    isTriggeringPipeline || (pipelineRuns ?? []).some((job) => isPipelineActive(job.status));

  // Queues the whole pipeline. A failure to queue (e.g. a 409 because the run
  // already has an active job) is put in `error`.
  const runPipeline = async () => {
    setError(null);
    try {
      await triggerPipeline({ run_id: runId });
    } catch (err) {
      setError(err);
    }
  };

  return { steps, isBusy, runPipeline, error };
};
