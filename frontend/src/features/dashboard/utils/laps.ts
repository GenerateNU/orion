import { seriesColor, type Series } from "@components/charts/series";
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

// A selected lap's chart series slot, from its place among the selected laps, so
// colors only repeat when more than 8 (the number of series colors) are selected.
// Pass the same `selectedLaps` everywhere, so a lap has one color on the strip,
// the map and the charts.
export function lapSeries(lapId: number, selectedLaps: readonly number[]): Series {
  return ((Math.max(selectedLaps.indexOf(lapId), 0) % 8) + 1) as Series;
}

export function lapColor(lapId: number, selectedLaps: readonly number[]): string {
  return seriesColor(lapSeries(lapId, selectedLaps));
}
