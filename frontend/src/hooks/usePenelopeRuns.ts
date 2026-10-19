import { useQuery } from "@tanstack/react-query";
import {
  PenelopeRunResponseSchema,
  type PenelopeRunResponse,
} from "@schemas/penelopeRun.schema";
import axios from "@api/client";
import { penelopeRunKeys } from "@api/queryKeys";
import { apiUrls } from "@utils/urls";
import { z } from "zod";

const PenelopeRunListSchema = z.array(PenelopeRunResponseSchema);

// Hook for listing every run recorded in Penelope, each flagged `processed`.
// Fails with 503 if Penelope isn't configured, or 502 if it's unreachable (VPN off).
export const usePenelopeRuns = () => {
  const query = useQuery({
    queryKey: penelopeRunKeys.all,
    queryFn: async (): Promise<PenelopeRunResponse[]> => {
      const { data } = await axios.get(apiUrls.penelopeRuns());

      const result = PenelopeRunListSchema.safeParse(data);
      if (!result.success) {
        throw new Error(`Data validation failed: ${result.error.message}`);
      }
      return result.data;
    },
  });

  return {
    penelopeRuns: query.data,
    penelopeRunsIsLoading: query.isLoading,
    penelopeRunsError: query.error,
    penelopeRunsRefetch: query.refetch,
  };
};
