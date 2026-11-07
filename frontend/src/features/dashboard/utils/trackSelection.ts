import { clamp, type RunTime, type TimeWindow } from "@features/dashboard/utils/time";

// The track map's selection: a point in the run and the window viewed around it.
// The map draws the window's bounds as notches behind and ahead of the point.
export type TrackSelection = {
  point: RunTime;
  window: TimeWindow;
};

// What can be dragged on the map: the point, or the notch at either bound.
export type TrackHandle = "point" | "start" | "end";

export const DEFAULT_HALF_WIDTH_MS = 5_000;
const MIN_HALF_WIDTH_MS = 250;

// The window `halfWidth` either side of `point`, clipped to the run.
export function centredSelection(
  point: RunTime,
  halfWidth: number,
  durationMs: number,
): TrackSelection {
  const centre = clamp(point, 0, durationMs);
  const half = Math.max(halfWidth, MIN_HALF_WIDTH_MS);
  return {
    point: centre,
    window: [Math.max(0, centre - half), Math.min(durationMs, centre + half)],
  };
}

// How far the window reaches from its point: the wider side, so a window clipped
// at the run's start or end gets its width back when the point moves away.
export const halfWidth = ({ point, window }: TrackSelection): number =>
  Math.max(point - window[0], window[1] - point);

// The selection the map shows for the dashboard's point and window. With no point
// (a window set by laps or another panel) the window's middle stands in for it;
// with neither, nothing is selected.
export function resolveSelection(
  point: RunTime | null,
  window: TimeWindow | null,
  durationMs: number,
): TrackSelection | null {
  if (point === null) return window ? { point: (window[0] + window[1]) / 2, window } : null;
  return { point, window: window ?? [0, durationMs] };
}
