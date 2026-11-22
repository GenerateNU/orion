import { useQuery } from "@tanstack/react-query";
import { LapsResponseSchema, type LapsResponse } from "@schemas/lap.schema";
import axios from "@api/client";
import { runDataKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";

// Hook for the lap step's output (OrionDB `laps`) for one run.
export const useRunLaps = <TData = LapsResponse>(
  runId: string | undefined,
  options: DataQueryOptions<LapsResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runDataKeys.laps(runId),
    queryFn: async (): Promise<LapsResponse> => {
      if (!runId) {
        throw new Error("Run ID is required");
      }

      const { data } = await axios.get(apiUrls.laps(runId));

      const result = LapsResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && (options.enabled ?? true),
  });

  return {
    laps: query.data,
    lapsIsLoading: query.isLoading,
    lapsIsFetching: query.isFetching,
    lapsError: query.error,
    lapsRefetch: query.refetch,
  };
};
