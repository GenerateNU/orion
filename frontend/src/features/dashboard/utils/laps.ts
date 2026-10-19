import type { MetricsResponse } from "@schemas/metrics.schema";
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
