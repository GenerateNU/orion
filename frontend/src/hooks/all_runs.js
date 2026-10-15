import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useRuns() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRuns() {
      try {
        const result = await apiClient("/api/runs");
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchRuns();
  }, []);

  return {
    data,
    isLoading,
    error,
  };
}