import { useEffect, useMemo, useRef } from "react";
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  PipelineRunResponseSchema,
  isPipelineActive,
  type PipelineRunCreate,
  type PipelineRunFilters,
  type PipelineRunResponse,
  type PipelineStatus,
} from "@schemas/pipeline.schema";
import axios from "@api/client";
import { penelopeRunKeys, pipelineRunKeys, runDataKeys, runKeys } from "@api/queryKeys";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const PipelineRunListSchema = z.array(PipelineRunResponseSchema);

// How often a queued/running job is re-fetched. There's no SSE endpoint yet.
const PIPELINE_POLL_MS = 2000;

// After a job finishes, the run lists show its new status. A successful job also
// rewrote the run's data, so that one run's cached metadata and traces are refetched.
// Other runs' cached traces are left alone.
function invalidateAfterJob(queryClient: QueryClient, runId: string, status: PipelineStatus) {
  queryClient.invalidateQueries({ queryKey: runKeys.lists() });
  queryClient.invalidateQueries({ queryKey: penelopeRunKeys.all });
  if (status === "succeeded") {
    queryClient.invalidateQueries({ queryKey: runKeys.detail(runId) });
    queryClient.invalidateQueries({ queryKey: runDataKeys.all(runId) });
  }
}

// Hook for listing pipeline jobs, newest first. Polls while any listed job is queued
// or running; when one finishes, the affected queries are refreshed (invalidateAfterJob).
export const usePipelineRuns = (filters: PipelineRunFilters = {}) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: pipelineRunKeys.list(filters),
    queryFn: async (): Promise<PipelineRunResponse[]> => {
      const { data } = await axios.get(apiUrls.pipelineRuns(), { params: filters });

      const result = PipelineRunListSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    refetchInterval: (query) =>
      query.state.data?.some((job) => isPipelineActive(job.status)) ? PIPELINE_POLL_MS : false,
  });

  const activeJobIds = useMemo(
    () => query.data?.filter((job) => isPipelineActive(job.status)).map((job) => job.id) ?? [],
    [query.data],
  );
  const previousActiveJobIds = useRef<number[]>([]);
  useEffect(() => {
    const finishedJobIds = previousActiveJobIds.current.filter((id) => !activeJobIds.includes(id));
    previousActiveJobIds.current = activeJobIds;
    for (const job of query.data ?? []) {
      if (finishedJobIds.includes(job.id)) invalidateAfterJob(queryClient, job.run_id, job.status);
    }
  }, [activeJobIds, query.data, queryClient]);

  return {
    pipelineRuns: query.data,
    pipelineRunsIsLoading: query.isLoading,
    pipelineRunsError: query.error,
    pipelineRunsRefetch: query.refetch,
  };
};

// Hook for one pipeline job. Polls while it is queued or running; once it
// finishes, the affected queries are refreshed (invalidateAfterJob).
export const usePipelineRun = (jobId: number | undefined) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: pipelineRunKeys.detail(jobId),
    queryFn: async (): Promise<PipelineRunResponse> => {
      if (jobId === undefined) {
        throw new Error("Pipeline job ID is required");
      }

      const { data } = await axios.get(apiUrls.pipelineRun(jobId));

      const result = PipelineRunResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: jobId !== undefined,
    refetchInterval: (query) =>
      isPipelineActive(query.state.data?.status) ? PIPELINE_POLL_MS : false,
  });

  const runId = query.data?.run_id;
  const status = query.data?.status;
  useEffect(() => {
    if (!runId || (status !== "succeeded" && status !== "failed")) return;
    invalidateAfterJob(queryClient, runId, status);
    queryClient.invalidateQueries({ queryKey: pipelineRunKeys.all });
  }, [runId, status, queryClient]);

  return {
    pipelineRun: query.data,
    pipelineRunIsLoading: query.isLoading,
    pipelineRunError: query.error,
    pipelineRunRefetch: query.refetch,
  };
};

// Hook for pipeline mutations
export const usePipelineMutations = () => {
  const queryClient = useQueryClient();

  // Queues a job that runs every pipeline stage for the run. Rejects with a 409
  // ApiError if the run already has a queued or running job.
  const triggerMutation = useMutation({
    mutationFn: async (payload: PipelineRunCreate): Promise<PipelineRunResponse> => {
      const { data } = await axios.post(apiUrls.pipelineRuns(), payload);

      const result = PipelineRunResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineRunKeys.all });
    },
  });

  return {
    triggerPipeline: triggerMutation.mutateAsync,
    isTriggeringPipeline: triggerMutation.isPending,
    triggerPipelineError: triggerMutation.error,
  };
};
