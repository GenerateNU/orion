import type { RunResponse } from "@schemas/run.schema";
import { parseBackendTime } from "@utils/backendTime";

// The dashboard measures time as RunTime: milliseconds since the run's start_time.
// Charts, the URL and the store all use it; it becomes an ISO string only when a
// request is sent (toIsoRange).
export type RunTime = number;

// [start, end] in RunTime. `null` wherever a window is optional means the whole run.
export type TimeWindow = readonly [start: RunTime, end: RunTime];

// Where a run sits on the wall clock, the reference for every RunTime.
export type RunTimeline = {
  startMs: number;
  durationMs: number;
};

// How a route's time column needs its bounds:
//   "naive": OrionDB trace tables are `timestamp without time zone`, which reject an
//            aware datetime ("2026-10-01T14:02:11.000"); the /state route.
//   "utc":   Penelope's `data.time` is `timestamptz` ("2026-10-01T14:02:11.000Z");
//            the /sensors/data route.
export type RangeFormat = "naive" | "utc";

const toIso = (epochMs: number, format: RangeFormat): string => {
  const iso = new Date(epochMs).toISOString();
  return format === "naive" ? iso.slice(0, -1) : iso;
};

// null when the run has no recorded start, or neither an end nor a duration.
export function runTimeline(run: RunResponse): RunTimeline | null {
  if (!run.start_time) return null;
  const startMs = parseBackendTime(run.start_time);
  const endMs = run.end_time
    ? parseBackendTime(run.end_time)
    : run.duration_s !== null
      ? startMs + run.duration_s * 1000
      : null;
  return endMs === null ? null : { startMs, durationMs: Math.max(0, endMs - startMs) };
}

export const toRunTime = (timeline: RunTimeline, iso: string): RunTime =>
  parseBackendTime(iso) - timeline.startMs;

// The `start` / `end` query params of a trace route for a window of the run.
export function toIsoRange(
  timeline: RunTimeline,
  window: TimeWindow | null,
  format: RangeFormat,
): { start: string; end: string } {
  const [from, to] = window ?? [0, timeline.durationMs];
  return { start: toIso(timeline.startMs + from, format), end: toIso(timeline.startMs + to, format) };
}

// Windows snap outward to a grid of 0.5% of the run, so windows a few pixels apart
// share a query key and come from the cache instead of the network.
const SNAP_FRACTION = 0.005;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

// Clamps a window to the run and snaps it; null when it covers the whole run.
export function snapWindow(window: TimeWindow, durationMs: number): TimeWindow | null {
  const step = Math.max(1, Math.round(durationMs * SNAP_FRACTION));
  const lo = Math.min(window[0], window[1]);
  const hi = Math.max(window[0], window[1]);
  const start = clamp(Math.floor(lo / step) * step, 0, durationMs);
  const end = clamp(Math.max(Math.ceil(hi / step) * step, start + step), start, durationMs);
  return start === 0 && end === durationMs ? null : [start, end];
}
