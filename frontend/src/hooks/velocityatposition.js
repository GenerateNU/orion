import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useVelocityAtPosition(
  raceId,
  lapNumber,
  latitude,
  longitude
) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchVelocity() {
      try {
        const params = new URLSearchParams({
          latitude: latitude,
          longitude: longitude,
        });

        const result = await apiClient(
          `/api/races/${raceId}/laps/${lapNumber}/velocity-at-position?${params}`
        );

        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchVelocity();
  }, [raceId, lapNumber, latitude, longitude]);

  return {
    data,
    isLoading,
    error,
  };
}