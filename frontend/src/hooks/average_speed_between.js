import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function useAverageSpeedBetween(
  raceId,
  lapNumber,
  startLatitude,
  startLongitude,
  endLatitude,
  endLongitude
) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchAverageSpeedBetween() {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          start_latitude: startLatitude,
          start_longitude: startLongitude,
          end_latitude: endLatitude,
          end_longitude: endLongitude,
        });

        const endpoint =
          `/api/races/${raceId}/laps/${lapNumber}/average-speed-between?${params}`;

        const result = await apiClient(endpoint);

        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchAverageSpeedBetween();
  }, [
    raceId,
    lapNumber,
    startLatitude,
    startLongitude,
    endLatitude,
    endLongitude,
  ]);

  return {
    data,
    isLoading,
    error,
  };
}