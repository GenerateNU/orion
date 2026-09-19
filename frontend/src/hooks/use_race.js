import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useRaces() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRaces() {
      try {
        const result = await apiClient("/api/races");
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchRaces();
  }, []);

  return {
    data,
    isLoading,
    error,
  };
}