import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useEnergy(runId, lapNumber) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchEnergy() {
      try {
        const result = await apiClient(
          `/api/runs/${runId}/laps/${lapNumber}/energy`
        );
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchEnergy();
  }, [runId, lapNumber]);

  return {
    data,
    isLoading,
    error,
  };
}