import type { MetricsResponse } from "@schemas/metrics.schema";
import type { SensorSeries } from "@schemas/sensor.schema";
import { toRunTime, type RunTimeline, type TimeWindow } from "@features/dashboard/utils/time";

// A lap as the dashboard uses it: its id and where it sits in the run.
export type Lap = {
  id: number;
  window: TimeWindow;
};

export function lapsFromMetrics(metrics: MetricsResponse, timeline: RunTimeline): Lap[] {
  return metrics.laps.map((lap) => ({
    id: lap.lap_id,
    window: [toRunTime(timeline, lap.start_time), toRunTime(timeline, lap.end_time)],
  }));
}

// The window spanning the given laps, or null when none of them are known.
export function lapsToWindow(laps: readonly Lap[], lapIds: readonly number[]): TimeWindow | null {
  const selected = laps.filter((lap) => lapIds.includes(lap.id));
  if (selected.length === 0) return null;
  return [
    Math.min(...selected.map((lap) => lap.window[0])),
    Math.max(...selected.map((lap) => lap.window[1])),
  ];
}

// One lap of a sensor, placed by how far round the lap each reading was taken.
export type LapTrace = {
  lapId: number;
  // 0-100, ascending.
  percent: number[];
  values: number[];
};

// A sensor's readings split into one trace per lap, by `lap_id` and
// `lap_percent` (fetched with `with_lap_percent`), using each reading's first
// value. Readings with no lap, no percentage or no value are left out. Laps come
// back in order; empty when the series has no lap percentages.
export function lapTraces(series: SensorSeries): LapTrace[] {
  const byLap = new Map<number, [number, number][]>();
  for (let i = 0; i < series.time.length; i++) {
    const lapId = series.lap_id?.[i];
    const percent = series.lap_percent?.[i];
    const value = series.values[i]?.[0];
    if (lapId == null || percent == null || value == null) continue;
    const points = byLap.get(lapId) ?? [];
    points.push([percent, value]);
    byLap.set(lapId, points);
  }
  return [...byLap]
    .sort(([a], [b]) => a - b)
    .map(([lapId, points]) => {
      points.sort((a, b) => a[0] - b[0]);
      return {
        lapId,
        percent: points.map(([percent]) => percent),
        values: points.map(([, value]) => value),
      };
    });
}
