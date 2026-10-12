import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useLap(runId, lapNumber) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchLap() {
      try {
        const result = await apiClient(
          `/api/runs/${runId}/laps/${lapNumber}`
        );
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchLap();
  }, [runId, lapNumber]);

  return {
    data,
    isLoading,
    error,
  };
}