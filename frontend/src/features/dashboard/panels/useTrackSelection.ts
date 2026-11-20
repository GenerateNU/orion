import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
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
const DEFAULT_HALF_M = 100;
const MIN_HALF_M = 5;

// A half-length that fits the run: at most half the distance driven.
export const clampHalf = (track: Track, halfM: number) =>
  Math.min(Math.max(halfM, MIN_HALF_M), Math.max(MIN_HALF_M, track.totalM / 2));

// The selection as the time window other panels use.
export const selectionWindow = (track: Track, s: TrackSelection): TimeWindow => {
  const at = distanceAt(track, s.center);
  return [timeAtDistance(track, at - s.halfM, "start"), timeAtDistance(track, at + s.halfM, "end")];
};

// The selection for a time window: its middle in distance, and half its length.
const selectionFor = (track: Track, range: TimeWindow): TrackSelection => {
  const from = distanceAt(track, range[0]);
  const to = distanceAt(track, range[1]);
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

// A selection the user moved on the map, and the URL windows it belongs to.
type Moved = {
  selection: TrackSelection;
  // The committed window when the move started.
  base: TimeWindow | null;
  // Once committed: the clamped window written to the URL.
  sent?: TimeWindow | null;
};

/**
 * Holds the selection locally while it's dragged, and commits it to the URL on
 * release. Other panels only read the committed window, so nothing is broadcast
 * mid-drag: no draft to clamp, cancel or clean up.
 *
 * Otherwise the selection is worked out from the URL during render, so it's
 * there on the first frame the track is. The URL holds the committed window
 * clamped to the run (an edge past the start or end is cut off), so it can't
 * always give back the car time: the map keeps the exact selection it moved
 * while the URL still holds the window that move produced, and goes back to the
 * URL's when it changes for another reason (lap selection, a reset, Back, a
 * pasted link).
 */
export function useTrackSelection(track: Track | null) {
  const { timeline } = useDashboardRun();
  const committed = useCommittedWindow();
  const { commitWindow } = useDashboardActions();

  const [moved, setMoved] = useState<Moved | null>(null);

  const fromUrl = useMemo(
    () => (track ? (committed ? selectionFor(track, committed) : defaultSelection(track)) : null),
    [track, committed],
  );
  // Before a commit, the move belongs to the window it started from; after, to
  // the one it wrote (and not the old one, so Back to it shows that window).
  const ownsUrl =
    moved !== null &&
    (moved.sent !== undefined
      ? sameWindow(moved.sent, committed)
      : sameWindow(moved.base, committed));
  const selection = track && ownsUrl ? moved.selection : fromUrl;

  // Mirrors `selection` for pointer handlers, which run between renders.
  const selectionRef = useRef<TrackSelection | null>(selection);
  useLayoutEffect(() => {
    selectionRef.current = selection;
  });

  const update = useCallback(
    (next: TrackSelection) => {
      selectionRef.current = next;
      setMoved({ selection: next, base: committed });
    },
    [committed],
  );

  const commit = useCallback(() => {
    const current = selectionRef.current;
    if (!current || !track) return;
    const range = selectionWindow(track, current);
    // commitWindow clamps the same way; remember the result to recognise it above.
    const target = timeline ? clampWindow(range, timeline.durationMs) : range;
    setMoved({ selection: current, base: committed, sent: target });
    // Unchanged (a click on the car without moving it): don't write the same URL.
    if (!sameWindow(target, committed)) commitWindow(range);
  }, [track, timeline, committed, commitWindow]);

  return {
    // Null only while there's no track.
    selection,
    selectionRef,
    // Moves the selection on the map only. Other panels see it once committed.
    update,
    commit,
    // False until a window is in the URL: the default ±100 m is only a suggestion.
    applied: committed !== null,
  };
}
