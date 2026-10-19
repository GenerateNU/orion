import { useQuery } from "@tanstack/react-query";
import {
  StateDataResponseSchema,
  type StateDataQuery,
  type StateDataResponse,
} from "@schemas/state.schema";
import axios from "@api/client";
import { runDataKeys } from "@api/queryKeys";
import type { DataQueryOptions } from "@api/queryOptions";
import { apiUrls } from "@utils/urls";

// Hook for the state estimation stage's output (OrionDB `estimated_car_state`):
// estimated [lat, lon] positions for one run between `start` and `end`.
export const useStateEstimation = <TData = StateDataResponse>(
  runId: string | undefined,
  range: StateDataQuery | undefined,
  options: DataQueryOptions<StateDataResponse, TData> = {},
) => {
  const query = useQuery({
    ...options,
    queryKey: runDataKeys.state(runId, range),
    queryFn: async (): Promise<StateDataResponse> => {
      if (!runId || !range) {
        throw new Error("Run ID and range are required");
      }

      const { data } = await axios.get(apiUrls.state(runId), { params: range });

      const result = StateDataResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && !!range && (options.enabled ?? true),
  });

  return {
    stateData: query.data,
    stateDataIsLoading: query.isLoading,
    stateDataIsFetching: query.isFetching,
    stateDataIsPlaceholderData: query.isPlaceholderData,
    stateDataError: query.error,
    stateDataRefetch: query.refetch,
  };
};
