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

// The stretch of the lap driven between two times (epoch ms). One across the
// start/finish line keeps only its part before the line. Null outside the points.
export function progressRangeBetween(
  points: LapProgressPoints,
  from: number,
  to: number,
): ProgressRange | null {
  const { progress, lapId } = progressAtTimes([from, to], points);
  const [start, end] = progress;
  if (start === null || end === null) return null;
  return lapId[0] === lapId[1] ? [start, end] : [start, 1];
}

// When a lap was in `range`: the times (epoch ms) of its longest unbroken run of
// points there, and how much of the range that run covers. Null if none.
export function lapStretch(points: LapProgressPoints, lapId: number, [start, end]: ProgressRange) {
  let best: { from: number; to: number; covers: number } | null = null;
  let first = -1;
  for (let i = 0; i <= points.time.length; i++) {
    const inside =
      i < points.time.length &&
      points.lapId[i] === lapId &&
      points.progress[i] >= start &&
      points.progress[i] <= end;
    if (inside && first < 0) first = i;
    if (inside || first < 0) continue;
    const covers = points.progress[i - 1] - points.progress[first];
    if (!best || covers > best.covers) {
      best = { from: points.time[first], to: points.time[i - 1], covers };
    }
    first = -1;
  }
  return best;
}

// The lap the track map draws: the lowest selected lap with points, else the lap
// covering the most of the lap (the first one on a tie). Null with no points.
export function mapLap(points: LapProgressPoints, selectedLaps: readonly number[]): number | null {
  const lapIds = new Set(points.lapId);
  const selected = selectedLaps.find((lapId) => lapIds.has(lapId));
  if (selected !== undefined) return selected;
  let best: { lapId: number; covers: number } | null = null;
  for (const lapId of lapIds) {
    const covers = lapStretch(points, lapId, [0, 1])?.covers ?? -1;
    if (!best || covers > best.covers) best = { lapId, covers };
  }
  return best?.lapId ?? null;
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
