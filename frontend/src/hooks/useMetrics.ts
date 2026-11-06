import { useQuery } from "@tanstack/react-query";
import { MetricsResponseSchema, type MetricsResponse } from "@schemas/metrics.schema";
import axios from "@api/client";
import { runDataKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";

// Hook for the laps of one run (OrionDB `metrics`). Fake laps for now, written by
// hand; the pipeline's lap step will fill the same table.
export const useMetrics = <TData = MetricsResponse>(
  runId: string | undefined,
  options: DataQueryOptions<MetricsResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runDataKeys.metrics(runId),
    queryFn: async (): Promise<MetricsResponse> => {
      if (!runId) {
        throw new Error("Run ID is required");
      }

      const { data } = await axios.get(apiUrls.metrics(runId));

      const result = MetricsResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && (options.enabled ?? true),
  });

  return {
    metrics: query.data,
    metricsIsLoading: query.isLoading,
    metricsIsFetching: query.isFetching,
    metricsError: query.error,
    metricsRefetch: query.refetch,
  };
};
