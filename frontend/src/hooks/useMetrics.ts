import { useQuery } from "@tanstack/react-query";
import { MetricsResponseSchema, type MetricsResponse } from "@schemas/metrics.schema";
import { RunResponseSchema } from "@schemas/run.schema";
import axios from "@api/client";
import { runDataKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { parseBackendTime } from "@utils/backendTime";
import { apiUrls } from "@utils/urls";

// TEMP: fake laps until the lap step and GET /runs/{run_id}/metrics exist.
// Essentially creates fake data by splitting the full run time into 5
// laps to be able to test and identify how metrics show up on front end
const FAKE_LAP_COUNT = 5;

async function fetchFakeMetrics(runId: string): Promise<unknown> {
  const { data } = await axios.get(apiUrls.run(runId));
  const run = RunResponseSchema.parse(data);
  if (!run.start_time || !run.end_time) return { run_id: runId, laps: [] };

  const startMs = parseBackendTime(run.start_time);
  const lapMs = (parseBackendTime(run.end_time) - startMs) / FAKE_LAP_COUNT;
  return {
    run_id: runId,
    laps: Array.from({ length: FAKE_LAP_COUNT }, (_, i) => ({
      lap_id: i + 1,
      start_time: new Date(startMs + i * lapMs).toISOString(),
      end_time: new Date(startMs + (i + 1) * lapMs).toISOString(),
    })),
  };
}

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

      const data = await fetchFakeMetrics(runId); // TEMP: was axios.get(apiUrls.metrics(runId))

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
