import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useVelocityAtPosition(
  runId,
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
          `/api/runs/${runId}/laps/${lapNumber}/velocity-at-position?${params}`
        );

        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchVelocity();
  }, [runId, lapNumber, latitude, longitude]);

  return {
    data,
    isLoading,
    error,
  };
}