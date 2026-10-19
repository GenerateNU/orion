import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  PipelineRunResponseSchema,
  isPipelineActive,
  type PipelineRunCreate,
  type PipelineRunFilters,
  type PipelineRunResponse,
} from "@schemas/pipeline.schema";
import axios from "@api/client";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const PipelineRunListSchema = z.array(PipelineRunResponseSchema);

// How often a queued/running job is re-fetched. There's no SSE endpoint yet.
const PIPELINE_POLL_MS = 2000;

// Hook for listing pipeline jobs, newest first
export const usePipelineRuns = (filters: PipelineRunFilters = {}) => {
  const query = useQuery({
    queryKey: ["pipeline-runs", filters],
    queryFn: async (): Promise<PipelineRunResponse[]> => {
      const { data } = await axios.get(apiUrls.pipelineRuns(), { params: filters });

      const result = PipelineRunListSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
  });

  return {
    pipelineRuns: query.data,
    pipelineRunsIsLoading: query.isLoading,
    pipelineRunsError: query.error,
    pipelineRunsRefetch: query.refetch,
  };
};

// Hook for one pipeline job. Polls while it is queued or running; once it
// succeeds, the run lists are refreshed so the run shows up as processed.
export const usePipelineRun = (jobId: number | undefined) => {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["pipeline-runs", jobId],
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

  const status = query.data?.status;
  useEffect(() => {
    if (status === "succeeded") {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["penelope-runs"] });
    }
    if (status === "succeeded" || status === "failed") {
      queryClient.invalidateQueries({ queryKey: ["pipeline-runs"], exact: false });
    }
  }, [status, queryClient]);

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
      queryClient.invalidateQueries({ queryKey: ["pipeline-runs"] });
    },
  });

  return {
    triggerPipeline: triggerMutation.mutateAsync,
    isTriggeringPipeline: triggerMutation.isPending,
    triggerPipelineError: triggerMutation.error,
  };
};
