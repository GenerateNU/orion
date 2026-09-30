import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

export function usePositionsByBounds(
  raceId,
  lapNumber,
  minLat,
  maxLat,
  minLon,
  maxLon
) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchPositions() {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();

        if (minLat !== undefined && minLat !== null) {
          params.append("min_lat", minLat);
        }

        if (maxLat !== undefined && maxLat !== null) {
          params.append("max_lat", maxLat);
        }

        if (minLon !== undefined && minLon !== null) {
          params.append("min_lon", minLon);
        }

        if (maxLon !== undefined && maxLon !== null) {
          params.append("max_lon", maxLon);
        }

        const queryString = params.toString();

        const endpoint =
          `/api/races/${raceId}/laps/${lapNumber}/positions` +
          (queryString ? `?${queryString}` : "");

        const result = await apiClient(endpoint);

        setData(result);
      } catch (err) {
        setError(err);
      } finally {
        setIsLoading(false);
      }
    }

    fetchPositions();
  }, [raceId, lapNumber, minLat, maxLat, minLon, maxLon]);

  return {
    data,
    isLoading,
    error,
  };
}