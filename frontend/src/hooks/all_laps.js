import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useLaps(runId) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchLaps() {
      try {
        const result = await apiClient(`/api/runs/${runId}/laps`);
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchLaps();
  }, [runId]);

  return {
    data,
    isLoading,
    error,
  };
}