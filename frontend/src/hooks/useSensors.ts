import { useQuery } from "@tanstack/react-query";
import {
  LapSensorDataResponseSchema,
  SensorDataResponseSchema,
  SensorResponseSchema,
  type LapSensorDataQuery,
  type LapSensorDataResponse,
  type SensorDataQuery,
  type SensorDataResponse,
  type SensorResponse,
} from "@schemas/sensor.schema";
import axios from "@api/client";
import { runDataKeys, sensorKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const SensorListSchema = z.array(SensorResponseSchema);

// Both routes read Penelope directly: they fail with 503 if it isn't configured,
// or 502 if it's unreachable (VPN off).

// Hook for listing Penelope's sensor types (`data_type`), each with its unit.
export const useSensors = () => {
  const query = useQuery({
    queryKey: sensorKeys.all,
    queryFn: async (): Promise<SensorResponse[]> => {
      const { data } = await axios.get(apiUrls.sensors());

      const result = SensorListSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    staleTime: Infinity,
  });

  return {
    sensors: query.data,
    sensorsIsLoading: query.isLoading,
    sensorsError: query.error,
    sensorsRefetch: query.refetch,
  };
};

// Hook for raw readings of `range.sensors` (Penelope `dataTypeName`s) for one run
// between `start` and `end`, as the car sent them, not downsampled.
export const useSensorData = <TData = SensorDataResponse>(
  runId: string | undefined,
  range: SensorDataQuery | undefined,
  options: DataQueryOptions<SensorDataResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runDataKeys.sensors(runId, range),
    queryFn: async (): Promise<SensorDataResponse> => {
      if (!runId || !range) {
        throw new Error("Run ID and range are required");
      }

      const { data } = await axios.get(apiUrls.sensorData(runId), {
        params: { ...range, sensors: range.sensors.join(",") },
      });

      const result = SensorDataResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && !!range && range.sensors.length > 0 && (options.enabled ?? true),
  });

  return {
    sensorData: query.data,
    sensorDataIsLoading: query.isLoading,
    sensorDataIsFetching: query.isFetching,
    sensorDataIsPlaceholderData: query.isPlaceholderData,
    sensorDataError: query.error,
    sensorDataRefetch: query.refetch,
  };
};

// Hook for readings of `range.sensors` during each lap in `range.lap_ids`, the
// whole lap, with each reading's lap percent: one response per lap, in order.
// Fails with 404 for a run with no lap percents.
export const useLapSensorData = <TData = LapSensorDataResponse>(
  runId: string | undefined,
  range: LapSensorDataQuery | undefined,
  options: DataQueryOptions<LapSensorDataResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runDataKeys.lapSensors(runId, range),
    queryFn: async (): Promise<LapSensorDataResponse> => {
      if (!runId || !range) {
        throw new Error("Run ID and range are required");
      }

      // `lap_ids` repeats per lap (`lap_ids=3&lap_ids=5`), as the route expects.
      const { data } = await axios.get(apiUrls.lapSensorData(runId), {
        params: { ...range, sensors: range.sensors.join(",") },
        paramsSerializer: { indexes: null },
      });

      const result = LapSensorDataResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled:
      !!runId &&
      !!range &&
      range.sensors.length > 0 &&
      range.lap_ids.length > 0 &&
      (options.enabled ?? true),
  });

  return {
    lapSensorData: query.data,
    lapSensorDataIsLoading: query.isLoading,
    lapSensorDataError: query.error,
  };
};
