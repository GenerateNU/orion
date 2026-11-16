import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import axios from "@api/client";
import {
  PIPELINE_POLL_MS,
  invalidateAfterJob,
  usePipelineMutations,
  usePipelineRuns,
} from "@hooks/usePipelineRuns";
import {
  PIPELINE_STEPS,
  PipelineRunResponseSchema,
  isPipelineActive,
  type PipelineRunResponse,
  type PipelineStep,
} from "@schemas/pipeline.schema";
import { apiUrls } from "@utils/urls";

export type StepStatus = "idle" | "running" | "succeeded" | "failed" | "skipped";

export type StepState = {
  step: PipelineStep;
  status: StepStatus;
  // When the step's latest job was queued (jobs don't record a finish time).
  lastRunAt: string | undefined;
  error: string | null;
  // An earlier step succeeded more recently than this one, so its output is out of date.
  stale: boolean;
};

// A whole-pipeline job (step null) counts as a run of every step.
const ranStep = (job: PipelineRunResponse, step: PipelineStep) =>
  job.step === step || job.step === null;

// Polls one job until it's no longer queued or running.
async function waitForJob(jobId: number): Promise<PipelineRunResponse> {
  for (;;) {
    await new Promise((resolve) => setTimeout(resolve, PIPELINE_POLL_MS));
    const { data } = await axios.get(apiUrls.pipelineRun(jobId));
    const job = PipelineRunResponseSchema.parse(data);
    if (!isPipelineActive(job.status)) return job;
  }
}

// Per-step pipeline status for one run, and actions to re-run one step or all of
// them in order. Job polling and refetching the run's data after a job finishes
// come from usePipelineRuns.
export const usePipelineSteps = (runId: string) => {
  const queryClient = useQueryClient();
  const { pipelineRuns } = usePipelineRuns({ run_id: runId });
  const { triggerPipeline } = usePipelineMutations();
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [skipped, setSkipped] = useState<readonly PipelineStep[]>([]);
  const [error, setError] = useState<unknown>(null);

  const steps = useMemo((): StepState[] => {
    // Newest first, so find() gives each step's latest job.
    const jobs = pipelineRuns ?? [];
    const lastSuccessMs = (step: PipelineStep) => {
      const job = jobs.find((j) => ranStep(j, step) && j.status === "succeeded");
      return job ? Date.parse(job.queued_at) : undefined;
    };

    return PIPELINE_STEPS.map((step, i) => {
      const job = jobs.find((j) => ranStep(j, step));
      const ownSuccess = lastSuccessMs(step);
      const stale =
        ownSuccess !== undefined &&
        PIPELINE_STEPS.slice(0, i).some((upstream) => (lastSuccessMs(upstream) ?? 0) > ownSuccess);

      let status: StepStatus = "idle";
      if (skipped.includes(step)) status = "skipped";
      else if (job) status = job.status === "queued" ? "running" : job.status;

      return {
        step,
        status,
        lastRunAt: job?.queued_at,
        error: job?.status === "failed" ? job.error : null,
        stale,
      };
    });
  }, [pipelineRuns, skipped]);

  const isBusy = isRunningAll || (pipelineRuns ?? []).some((job) => isPipelineActive(job.status));

  // Queues one step. A failure to queue (e.g. a 409 ApiError because the run
  // already has an active job) is put in `error`.
  const runStep = async (step: PipelineStep) => {
    setError(null);
    setSkipped((current) => current.filter((s) => s !== step));
    try {
      await triggerPipeline({ run_id: runId, step });
    } catch (err) {
      setError(err);
    }
  };

  // Runs every step in order, one job each, waiting for each to finish. Stops at
  // the first failure and marks the steps after it as skipped.
  const runAll = async () => {
    setError(null);
    setSkipped([]);
    setIsRunningAll(true);
    let i = 0;
    try {
      for (; i < PIPELINE_STEPS.length; i++) {
        const queued = await triggerPipeline({ run_id: runId, step: PIPELINE_STEPS[i] });
        const done = await waitForJob(queued.id);
        invalidateAfterJob(queryClient, runId, done.status);
        if (done.status === "failed") {
          setSkipped(PIPELINE_STEPS.slice(i + 1));
          return;
        }
      }
    } catch (err) {
      setError(err);
      setSkipped(PIPELINE_STEPS.slice(i + 1));
    } finally {
      setIsRunningAll(false);
    }
  };

  return { steps, isBusy, runStep, runAll, error };
};
