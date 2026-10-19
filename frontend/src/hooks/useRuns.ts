import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  RunResponseSchema,
  type RunListFilters,
  type RunResponse,
} from "@schemas/run.schema";
import axios from "@api/client";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const RunListSchema = z.array(RunResponseSchema);

// Hook for listing runs stored in OrionDB. `{ processed: true }` limits it to runs
// with a pipeline job that succeeded with no error.
export const useRuns = (filters: RunListFilters = {}) => {
  const query = useQuery({
    queryKey: ["runs", filters],
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
export const useRun = (runId: string | undefined) => {
  const query = useQuery({
    queryKey: ["runs", runId],
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
    enabled: !!runId,
  });

  return {
    run: query.data,
    runIsLoading: query.isLoading,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["penelope-runs"] });
    },
  });

  return {
    deleteRun: deleteMutation.mutateAsync,
    isDeletingRun: deleteMutation.isPending,
    deleteRunError: deleteMutation.error,
  };
};
