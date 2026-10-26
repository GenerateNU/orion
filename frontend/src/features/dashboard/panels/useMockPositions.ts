export function useMockPositions() {
  // eslint-disable-next-line no-loss-of-precision
  const runDurationUs = 115642993357766642;

  const time = Array.from({ length: 100 }, (_, i) => (i / 100) * runDurationUs);

  // x,y coordinates on an oval
  const positions = Array.from({ length: 100 }, (_, i) => {
    const angle = (i / 100) * 2 * Math.PI;
    const x = 150 + 150 * Math.cos(angle);
    const t = (i / 100) * Math.PI * 2;
    const y = 100 + 50 * Math.sin(t) * Math.sin(t / 2);
    return [x, y] as [number, number];
  });

  return { time, positions };
}

export function formatTime(microseconds: number): string {
  const seconds = Math.floor(microseconds / 1_000_000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}
