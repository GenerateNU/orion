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

// Lap percent needs an ideal lap, which needs at least 3 laps (docs/lap_progress.md),
// so only then are laps compared by percent.
export const MIN_LAPS_TO_COMPARE = 3;

// Shown instead of the track map and sensor charts while no lap is selected.
export const NO_LAPS_MESSAGE = "Select at least 1 lap to see its data.";

// One color per lap (lap ids start at 1), the same everywhere it's drawn. Cycles
// after 20 laps.
const LAP_COLORS = [
  "#1f77b4",
  "#aec7e8",
  "#ff7f0e",
  "#ffbb78",
  "#2ca02c",
  "#98df8a",
  "#d62728",
  "#ff9896",
  "#9467bd",
  "#c5b0d5",
  "#8c564b",
  "#c49c94",
  "#e377c2",
  "#f7b6d2",
  "#7f7f7f",
  "#c7c7c7",
  "#bcbd22",
  "#dbdb8d",
  "#17becf",
  "#9edae5",
];

export function lapColor(lapId: number): string {
  return LAP_COLORS[(lapId - 1) % LAP_COLORS.length];
}
