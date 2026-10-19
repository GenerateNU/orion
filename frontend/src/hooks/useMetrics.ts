import { useQuery } from "@tanstack/react-query";
import { MetricsResponseSchema, type MetricsResponse } from "@schemas/metrics.schema";
import axios from "@api/client";
import { runDataKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";

// Hook for the metrics stage's output (OrionDB `metrics`) for one run.
// PLANNED: there is no metrics step or backend route yet, so this fails with
// "... isn't available on the backend yet" until there is.
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
