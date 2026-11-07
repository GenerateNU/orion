import { useCallback, useEffect, useRef, useState } from "react";
import {
  useCommittedWindow,
  useDashboardActions,
  useDashboardRun,
} from "@features/dashboard/state/useDashboard";
import { distanceAt, timeAtDistance, type Track } from "@features/dashboard/utils/trackmap";
import { clampWindow, type RunTime, type TimeWindow } from "@features/dashboard/utils/time";

// The track map's selection: the car's time and `halfM` metres of road either
// side of it, so the window looks symmetric around the car on the map. Its time
// span usually isn't: the car covers the road faster on one side than the other.
export type TrackSelection = { center: RunTime; halfM: number };

// With no window in the URL, the window is the run's first 200 m, car in the middle.
export const DEFAULT_HALF_M = 100;
export const MIN_HALF_M = 5;

// A half-length that fits the run: at most half the distance driven.
export const clampHalf = (track: Track, halfM: number) =>
  Math.min(Math.max(halfM, MIN_HALF_M), Math.max(MIN_HALF_M, track.totalM / 2));

// The selection as the time window other panels use.
export const selectionWindow = (track: Track, s: TrackSelection): TimeWindow => {
  const at = distanceAt(track, s.center);
  return [timeAtDistance(track, at - s.halfM, "start"), timeAtDistance(track, at + s.halfM, "end")];
};

// The selection for a time window: its middle in distance, and half its length.
const selectionFor = (track: Track, window: TimeWindow): TrackSelection => {
  const from = distanceAt(track, window[0]);
  const to = distanceAt(track, window[1]);
  return {
    center: timeAtDistance(track, (from + to) / 2, "end"),
    halfM: clampHalf(track, (to - from) / 2),
  };
};

// The default selection: the run's first stretch of road, car in the middle, so
// the window starts at the first fix instead of half of it hanging before the data.
const defaultSelection = (track: Track): TrackSelection => {
  const halfM = clampHalf(track, DEFAULT_HALF_M);
  return { center: timeAtDistance(track, halfM, "end"), halfM };
};

const sameWindow = (a: TimeWindow | null, b: TimeWindow | null) =>
  a === b || (!!a && !!b && Math.abs(a[0] - b[0]) < 1 && Math.abs(a[1] - b[1]) < 1);

/**
 * Holds the selection locally while it's dragged, and commits it to the URL on
 * release. Other panels only read the committed window, so nothing is broadcast
 * mid-drag: no draft to clamp, cancel or clean up.
 *
 * The URL holds the committed window clamped to the run (an edge past the start
 * or end is cut off), so it can't always give back the car time. The map keeps
 * the exact selection here and re-reads the URL only when it changes for another
 * reason (lap selection, a reset, Back, a pasted link).
 */
export function useTrackSelection(track: Track | null) {
  const { timeline } = useDashboardRun();
  const committed = useCommittedWindow();
  const { commitWindow } = useDashboardActions();

  const [selection, setSelection] = useState<TrackSelection | null>(null);
  // Mirrors `selection` for pointer handlers, which run between renders.
  const selectionRef = useRef<TrackSelection | null>(null);
  // The clamped window this map last wrote to the URL; undefined when none.
  const sentRef = useRef<TimeWindow | null | undefined>(undefined);

  const set = useCallback((next: TrackSelection) => {
    selectionRef.current = next;
    setSelection(next);
  }, []);

  useEffect(() => {
    if (!track) return;
    // Our own commit coming back through the URL: keep the exact selection.
    if (sentRef.current !== undefined && sameWindow(sentRef.current, committed)) return;
    sentRef.current = undefined;
    set(committed ? selectionFor(track, committed) : defaultSelection(track));
  }, [track, committed, set]);

  const commit = useCallback(() => {
    const current = selectionRef.current;
    if (!current || !track) return;
    const window = selectionWindow(track, current);
    // commitWindow clamps the same way; remember the result to recognise it above.
    const target = timeline ? clampWindow(window, timeline.durationMs) : window;
    sentRef.current = target;
    // Unchanged (a click on the car without moving it): don't write the same URL.
    if (!sameWindow(target, committed)) commitWindow(window);
  }, [track, timeline, committed, commitWindow]);

  return {
    selection,
    selectionRef,
    // Moves the selection on the map only. Other panels see it once committed.
    update: set,
    commit,
    // False until a window is in the URL: the default ±100 m is only a suggestion.
    applied: committed !== null,
  };
}
