import { useCallback, useEffect, useRef, useState } from "react";
import {
  useCommittedWindow,
  useDashboardActions,
  useDashboardRun,
} from "@features/dashboard/state/useDashboard";
import type { Track } from "@features/dashboard/utils/trackmap";
import { clampWindow, type RunTime, type TimeWindow } from "@features/dashboard/utils/time";

// The track map's selection: the car's time and a window of `half` ms either
// side of it, so the window is always symmetric around the car.
export type TrackSelection = { center: RunTime; half: number };

// With no window in the URL, the window is the run's first 30 s, car in the middle.
export const DEFAULT_HALF_MS = 15_000;
export const MIN_HALF_MS = 1_000;

export const selectionWindow = (s: TrackSelection): TimeWindow => [
  s.center - s.half,
  s.center + s.half,
];

const sameWindow = (a: TimeWindow | null, b: TimeWindow | null) =>
  a === b || (!!a && !!b && Math.abs(a[0] - b[0]) < 1 && Math.abs(a[1] - b[1]) < 1);

/**
 * Holds the selection locally while it's dragged, previews it to other panels,
 * and commits it to the URL on release.
 *
 * The URL holds the committed window clamped to the run (an edge past the start
 * or end is cut off), so it can't always give back the car time. The map keeps
 * the exact selection here and re-reads the URL only when it changes for another
 * reason (lap selection, a reset, Back, a pasted link).
 */
export function useTrackSelection(track: Track | null) {
  const { timeline } = useDashboardRun();
  const committed = useCommittedWindow();
  const { previewWindow, commitWindow, cancelPreview } = useDashboardActions();

  const [selection, setSelection] = useState<TrackSelection | null>(null);
  // Mirrors `selection` for pointer handlers, which run between renders.
  const selectionRef = useRef<TrackSelection | null>(null);
  // The snapped window this map last wrote to the URL; undefined when none.
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
    set(
      committed
        ? { center: (committed[0] + committed[1]) / 2, half: (committed[1] - committed[0]) / 2 }
        : // Centred 15 s in, so the window starts at the first fix instead of
          // half of it hanging before the data with its handle under the car.
          { center: track.firstTime + DEFAULT_HALF_MS, half: DEFAULT_HALF_MS },
    );
  }, [track, committed, set]);

  const preview = useCallback(
    (next: TrackSelection) => {
      set(next);
      previewWindow(selectionWindow(next));
    },
    [set, previewWindow],
  );

  const commit = useCallback(() => {
    const current = selectionRef.current;
    if (!current) return;
    const window = selectionWindow(current);
    // commitWindow clamps the same way; remember the result to recognise it above.
    sentRef.current = timeline ? clampWindow(window, timeline.durationMs) : window;
    commitWindow(window);
  }, [timeline, commitWindow]);

  const cancel = useCallback(
    (restore: TrackSelection) => {
      set(restore);
      cancelPreview();
    },
    [set, cancelPreview],
  );

  return {
    selection,
    selectionRef,
    preview,
    commit,
    cancel,
    // False until a window is in the URL: the default ±15 s is only a suggestion.
    applied: committed !== null,
  };
}
