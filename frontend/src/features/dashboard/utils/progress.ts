// Lap progress: how far through its lap the car is, from 0 to 1 (docs/lap_progress.md).

export type LapProgressPoints = {
  // Epoch ms, ascending.
  time: Float64Array;
  progress: number[];
  lapId: number[];
};

// A stretch of the lap, [start, end] with 0 <= start < end <= 1.
export type ProgressRange = readonly [start: number, end: number];

const snapProgress = (value: number) =>
  Math.round(Math.min(Math.max(value, 0), 1) * 10_000) / 10_000;

// Clamped to the lap and rounded to 4 decimals, so the URL stays short.
export const snapProgressRange = ([start, end]: ProgressRange): ProgressRange => [
  snapProgress(start),
  snapProgress(end),
];

export type ReadingProgress = {
  progress: (number | null)[];
  lapId: (number | null)[];
};

// Each reading takes the progress and lap of the point nearest to it in time.
// Readings before the first point or after the last get null.
export function progressAtTimes(
  times: ArrayLike<number>,
  points: LapProgressPoints,
): ReadingProgress {
  const last = points.time.length - 1;
  const result: ReadingProgress = { progress: [], lapId: [] };
  for (let i = 0; i < times.length; i++) {
    const t = times[i];
    if (last < 0 || t < points.time[0] || t > points.time[last]) {
      result.progress.push(null);
      result.lapId.push(null);
      continue;
    }
    const nearest = nearestIndex(points.time, t);
    result.progress.push(points.progress[nearest]);
    result.lapId.push(points.lapId[nearest]);
  }
  return result;
}

// Index of the value in `sorted` closest to `t`; ties go to the earlier one.
function nearestIndex(sorted: Float64Array, t: number): number {
  let low = 0;
  let high = sorted.length - 1;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (sorted[mid] < t) low = mid + 1;
    else high = mid;
  }
  return low > 0 && t - sorted[low - 1] <= sorted[low] - t ? low - 1 : low;
}
