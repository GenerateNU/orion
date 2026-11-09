import { useQuery } from "@tanstack/react-query";
import {
  DerivedMetricResponseSchema,
  type DerivedMetricQuery,
  type DerivedMetricResponse,
} from "@schemas/derivedMetric.schema";
import { SensorDataResponseSchema, type SensorDataResponse } from "@schemas/sensor.schema";
import axios from "@api/client";
import { derivedMetricKeys, runDataKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const DerivedMetricListSchema = z.array(DerivedMetricResponseSchema);

// Metrics are computed on request from Penelope sensors, so these fail like the
// sensor routes: 503 if Penelope isn't configured, 502 if it's unreachable.

// Hook for listing every registered derived metric, each with its unit.
export const useDerivedMetrics = () => {
  const query = useQuery({
    queryKey: derivedMetricKeys.all,
    queryFn: async (): Promise<DerivedMetricResponse[]> => {
      const { data } = await axios.get(apiUrls.derivedMetrics());

      const result = DerivedMetricListSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    staleTime: Infinity,
  });

  return {
    derivedMetrics: query.data,
    derivedMetricsIsLoading: query.isLoading,
    derivedMetricsError: query.error,
  };
};

// Hook for one derived metric over one run between `start` and `end`, returned as
// a single series keyed by `name`.
export const useDerivedMetricData = <TData = SensorDataResponse>(
  runId: string | undefined,
  name: string | undefined,
  range: DerivedMetricQuery | undefined,
  options: DataQueryOptions<SensorDataResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runDataKeys.derivedMetric(runId, name, range),
    queryFn: async (): Promise<SensorDataResponse> => {
      if (!runId || !name || !range) {
        throw new Error("Run ID, metric name and range are required");
      }

      const { data } = await axios.get(apiUrls.derivedMetricData(runId, name), {
        params: range,
      });

      const result = SensorDataResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && !!name && !!range && (options.enabled ?? true),
  });

  return {
    derivedMetricData: query.data,
    derivedMetricDataIsLoading: query.isLoading,
    derivedMetricDataIsPlaceholderData: query.isPlaceholderData,
    derivedMetricDataError: query.error,
  };
};
