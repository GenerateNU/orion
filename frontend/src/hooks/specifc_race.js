import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useRace(raceId) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRace() {
      try {
        const result = await apiClient(`/api/races/${raceId}`);
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchRace();
  }, [raceId]);

  return {
    data,
    isLoading,
    error,
  };
}