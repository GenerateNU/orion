import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useRun(runId) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRun() {
      try {
        const result = await apiClient(`/api/runs/${runId}`);
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchRun();
  }, [runId]);

  return {
    data,
    isLoading,
    error,
  };
}