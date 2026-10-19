import { useQuery } from "@tanstack/react-query";
import {
  CleanedDataResponseSchema,
  type CleanedDataQuery,
  type CleanedDataResponse,
} from "@schemas/cleanedData.schema";
import axios from "@api/client";
import { apiUrls } from "@utils/urls";

// Hook for the clean stage's output (OrionDB `cleaned_data`) for one run.
// PLANNED: the backend route doesn't exist yet, so this fails with
// "... isn't available on the backend yet" until it does.
export const useCleanedData = (runId: string | undefined, range: CleanedDataQuery | undefined) => {
  const query = useQuery({
    queryKey: ["runs", runId, "cleaned", range],
    queryFn: async (): Promise<CleanedDataResponse> => {
      if (!runId || !range) {
        throw new Error("Run ID and range are required");
      }

      const { data } = await axios.get(apiUrls.cleanedData(runId), {
        params: { ...range, sensors: range.sensors.join(",") },
      });

      const result = CleanedDataResponseSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
    enabled: !!runId && !!range && range.sensors.length > 0,
  });

  return {
    cleanedData: query.data,
    cleanedDataIsLoading: query.isLoading,
    cleanedDataError: query.error,
    cleanedDataRefetch: query.refetch,
  };
};
