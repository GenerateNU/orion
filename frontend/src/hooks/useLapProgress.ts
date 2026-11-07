import { useQuery } from "@tanstack/react-query";
import {
  LapProgressResponseSchema,
  type LapProgressQuery,
  type LapProgressResponse,
} from "@schemas/lapProgress.schema";
import axios from "@api/client";
import { runDataKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";

// Hook for how far through its lap the car is (docs/lap_progress.md), for one run
// between `start` and `end`.
export const useLapProgress = <TData = LapProgressResponse>(
  runId: string | undefined,
  range: LapProgressQuery | undefined,
  options: DataQueryOptions<LapProgressResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runDataKeys.lapProgress(runId, range),
    queryFn: async (): Promise<LapProgressResponse> => {
      if (!runId || !range) {
        throw new Error("Run ID and range are required");
      }

      const { data } = await axios.get(apiUrls.lapProgress(runId), { params: range });

      const result = LapProgressResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && !!range && (options.enabled ?? true),
  });

  return {
    lapProgress: query.data,
    lapProgressIsLoading: query.isLoading,
    lapProgressIsFetching: query.isFetching,
    lapProgressIsPlaceholderData: query.isPlaceholderData,
    lapProgressError: query.error,
    lapProgressRefetch: query.refetch,
  };
};
