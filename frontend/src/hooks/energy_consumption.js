import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useEnergy(raceId, lapNumber) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchEnergy() {
      try {
        const result = await apiClient(
          `/api/races/${raceId}/laps/${lapNumber}/energy`
        );
        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchEnergy();
  }, [raceId, lapNumber]);

  return {
    data,
    isLoading,
    error,
  };
}