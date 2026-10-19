import { useQuery } from "@tanstack/react-query";
import {
  StateDataResponseSchema,
  type StateDataQuery,
  type StateDataResponse,
} from "@schemas/state.schema";
import axios from "@api/client";
import { apiUrls } from "@utils/urls";

// Hook for the state estimation stage's output (OrionDB `estimated_car_state`):
// estimated [lat, lon] positions for one run between `start` and `end`.
export const useStateEstimation = (runId: string | undefined, range: StateDataQuery | undefined) => {
  const query = useQuery({
    queryKey: ["runs", runId, "state", range],
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
    enabled: !!runId && !!range,
  });

  return {
    stateData: query.data,
    stateDataIsLoading: query.isLoading,
    stateDataError: query.error,
    stateDataRefetch: query.refetch,
  };
};
