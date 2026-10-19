import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RunResponseSchema,
  type RunListFilters,
  type RunResponse,
} from "@schemas/run.schema";
import axios from "@api/client";
import { penelopeRunKeys, runDataKeys, runKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const RunListSchema = z.array(RunResponseSchema);

// Hook for listing runs stored in OrionDB. `{ processed: true }` limits it to runs
// with a pipeline job that succeeded with no error.
export const useRuns = (filters: RunListFilters = {}) => {
  const query = useQuery({
    queryKey: runKeys.list(filters),
    queryFn: async (): Promise<RunResponse[]> => {
      const { data } = await axios.get(apiUrls.runs(), { params: filters });

      const result = RunListSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
  });

  return {
    runs: query.data,
    runsIsLoading: query.isLoading,
    runsError: query.error,
    runsRefetch: query.refetch,
  };
};

// Hook for getting a single run
export const useRun = <TData = RunResponse>(
  runId: string | undefined,
  options: DataQueryOptions<RunResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runKeys.detail(runId),
    queryFn: async (): Promise<RunResponse> => {
      if (!runId) {
        throw new Error("Run ID is required");
      }

      const { data } = await axios.get(apiUrls.run(runId));

      const result = RunResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && (options.enabled ?? true),
  });

  return {
    run: query.data,
    runIsLoading: query.isLoading,
    runIsFetching: query.isFetching,
    runError: query.error,
    runRefetch: query.refetch,
  };
};

// Hook for run mutations. Runs are created by the pipeline, so only delete exists.
export const useRunMutations = () => {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: async (runId: string) => {
      await axios.delete(apiUrls.run(runId));
    },
    onSuccess: (_data, runId) => {
      queryClient.removeQueries({ queryKey: runKeys.detail(runId) });
      queryClient.removeQueries({ queryKey: runDataKeys.all(runId) });
      queryClient.invalidateQueries({ queryKey: runKeys.lists() });
      queryClient.invalidateQueries({ queryKey: penelopeRunKeys.all });
    },
  });

  return {
    deleteRun: deleteMutation.mutateAsync,
    isDeletingRun: deleteMutation.isPending,
    deleteRunError: deleteMutation.error,
  };
};
