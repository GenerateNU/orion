/**
 * Mock position data for TrackMap visualization.
 * Replace with useRunPositions('overview') when state_service is implemented.
 */
export function useMockPositions() {
  // Run duration in microseconds (~115 seconds)
  // eslint-disable-next-line no-loss-of-precision
  const runDurationUs = 115642993357766642;

  // Time array: 100 evenly-spaced points over the run duration
  const time = Array.from({ length: 100 }, (_, i) => (i / 100) * runDurationUs);

  // Position array: 0-100 (track progress), evenly distributed
  const positions = Array.from({ length: 100 }, (_, i) => (i / 100) * 100);

  return { time, positions };
}

export function formatTime(microseconds: number): string {
  const seconds = Math.floor(microseconds / 1_000_000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}
