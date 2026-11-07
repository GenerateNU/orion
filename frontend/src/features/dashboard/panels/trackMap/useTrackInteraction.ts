import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import {
  indexAtTime,
  nearestIndex,
  nearestIndexAround,
  pointAtTime,
  type TrackGeometry,
  type Vec2,
} from "@features/dashboard/utils/trackGeometry";
import {
  centredSelection,
  DEFAULT_HALF_WIDTH_MS,
  halfWidth,
  type TrackHandle,
  type TrackSelection,
} from "@features/dashboard/utils/trackSelection";
import type { RunTime } from "@features/dashboard/utils/time";
import { toScreen, toWorld, type ViewTransform } from "@features/dashboard/utils/trackView";

// The track map's input handling: turns pointer and key events on the map into
// selections and hover times. It draws nothing; the view takes `handlers` and
// shows `activeHandle` / `hoveredHandle` however it likes.
//
//   click the track     moves the point there (keeping the window's width)
//   drag the point      slides it along the path
//   drag a notch        widens or narrows the window, symmetrically
//   ← / →               steps the point (Shift for a bigger step)
//
// A drag previews on every frame and commits on release, like a chart brush.

export type TrackInteractionOptions = {
  geometry: TrackGeometry | null;
  transform: ViewTransform | null;
  durationMs: number;
  selection: TrackSelection | null;
  onPreview: (selection: TrackSelection) => void;
  onCommit: (selection: TrackSelection) => void;
  onDiscard: () => void;
  onHover: (time: RunTime | null) => void;
};

export type TrackInteractionHandlers = {
  onPointerDown: (event: PointerEvent<HTMLElement>) => void;
  onPointerMove: (event: PointerEvent<HTMLElement>) => void;
  onPointerUp: (event: PointerEvent<HTMLElement>) => void;
  onPointerCancel: (event: PointerEvent<HTMLElement>) => void;
  onPointerLeave: (event: PointerEvent<HTMLElement>) => void;
  onKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
};

export type TrackInteraction = {
  handlers: TrackInteractionHandlers;
  // Being dragged.
  activeHandle: TrackHandle | null;
  // Under the pointer, while nothing is dragged.
  hoveredHandle: TrackHandle | null;
};

// CSS pixels: how near the pointer must be to grab a handle, or to hit the track.
const HANDLE_REACH_PX = 14;
const TRACK_REACH_PX = 16;
// CSS pixels: passes about this close to the nearest one count as overlapping.
const OVERLAP_SLACK_PX = 4;
// How far along the path a dragged handle may travel in one frame.
const DRAG_SPAN_MS = 3_000;
const KEY_STEP_MS = 1_000;
const KEY_STEP_LARGE_MS = 10_000;

type Drag = {
  handle: TrackHandle;
  pointerId: number;
  // The sample the handle is on, where the next frame's search starts.
  index: number;
  selection: TrackSelection;
};

// Relative to the element's padding box, where its canvases are drawn.
function localPoint(event: PointerEvent<HTMLElement>): Vec2 {
  const element = event.currentTarget;
  const rect = element.getBoundingClientRect();
  return {
    x: event.clientX - rect.left - element.clientLeft,
    y: event.clientY - rect.top - element.clientTop,
  };
}

const currentHalfWidth = (selection: TrackSelection | null) =>
  selection ? halfWidth(selection) : DEFAULT_HALF_WIDTH_MS;

export function useTrackInteraction(options: TrackInteractionOptions): TrackInteraction {
  const [activeHandle, setActiveHandle] = useState<TrackHandle | null>(null);
  const [hoveredHandle, setHoveredHandle] = useState<TrackHandle | null>(null);

  // Handlers read the latest options through a ref, so they stay stable.
  const latest = useRef(options);
  useEffect(() => {
    latest.current = options;
  });

  const drag = useRef<Drag | null>(null);
  // Pointer moves are coalesced to one update per frame.
  const pendingMove = useRef<Vec2 | null>(null);
  const frame = useRef(0);
  useEffect(() => () => cancelAnimationFrame(frame.current), []);

  const handlers = useMemo((): TrackInteractionHandlers => {
    const handleAt = (screen: Vec2): TrackHandle | null => {
      const { geometry, transform, selection } = latest.current;
      if (!geometry || !transform || !selection) return null;
      const handles: [TrackHandle, RunTime][] = [
        ["point", selection.point],
        ["start", selection.window[0]],
        ["end", selection.window[1]],
      ];
      let hit: TrackHandle | null = null;
      let hitDistance = HANDLE_REACH_PX;
      for (const [handle, time] of handles) {
        const at = toScreen(transform, pointAtTime(geometry, time));
        const distance = Math.hypot(at.x - screen.x, at.y - screen.y);
        if (distance <= hitDistance) {
          hit = handle;
          hitDistance = distance;
        }
      }
      return hit;
    };

    const trackIndexAt = (screen: Vec2): number | null => {
      const { geometry, transform, selection } = latest.current;
      if (!geometry || !transform) return null;
      return nearestIndex(geometry, toWorld(transform, screen), {
        reach: TRACK_REACH_PX / transform.scale,
        slack: OVERLAP_SLACK_PX / transform.scale,
        preferTime: selection?.point ?? null,
      });
    };

    const dragTo = (screen: Vec2) => {
      const { geometry, transform, durationMs, onPreview } = latest.current;
      const current = drag.current;
      if (!current || !geometry || !transform) return;
      const index = nearestIndexAround(
        geometry,
        toWorld(transform, screen),
        current.index,
        DRAG_SPAN_MS,
      );
      const time = geometry.time[index];
      const { point } = current.selection;
      current.index = index;
      current.selection =
        current.handle === "point"
          ? centredSelection(time, halfWidth(current.selection), durationMs)
          : centredSelection(point, Math.abs(time - point), durationMs);
      onPreview(current.selection);
    };

    const hoverAt = (screen: Vec2) => {
      const { geometry, onHover } = latest.current;
      setHoveredHandle(handleAt(screen));
      const index = trackIndexAt(screen);
      onHover(index === null || !geometry ? null : geometry.time[index]);
    };

    const flushMove = () => {
      frame.current = 0;
      const screen = pendingMove.current;
      pendingMove.current = null;
      if (!screen) return;
      if (drag.current) dragTo(screen);
      else hoverAt(screen);
    };

    const endDrag = (event: PointerEvent<HTMLElement>) => {
      cancelAnimationFrame(frame.current);
      frame.current = 0;
      pendingMove.current = null;
      drag.current = null;
      setActiveHandle(null);
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
    };

    return {
      onPointerDown: (event) => {
        const { geometry, durationMs, selection, onPreview } = latest.current;
        if (event.button !== 0 || !geometry || drag.current) return;
        const screen = localPoint(event);

        const handle = handleAt(screen);
        let start: Drag;
        if (handle && selection) {
          const time =
            handle === "point" ? selection.point : selection.window[handle === "start" ? 0 : 1];
          start = {
            handle,
            pointerId: event.pointerId,
            index: indexAtTime(geometry.time, time),
            selection,
          };
        } else {
          // A click on the track moves the point there, then drags it.
          const index = trackIndexAt(screen);
          if (index === null) return;
          start = {
            handle: "point",
            pointerId: event.pointerId,
            index,
            selection: centredSelection(
              geometry.time[index],
              currentHalfWidth(selection),
              durationMs,
            ),
          };
          onPreview(start.selection);
        }

        drag.current = start;
        setActiveHandle(start.handle);
        setHoveredHandle(null);
        event.currentTarget.setPointerCapture(event.pointerId);
      },

      onPointerMove: (event) => {
        if (drag.current && drag.current.pointerId !== event.pointerId) return;
        pendingMove.current = localPoint(event);
        if (!frame.current) frame.current = requestAnimationFrame(flushMove);
      },

      onPointerUp: (event) => {
        const current = drag.current;
        if (!current || current.pointerId !== event.pointerId) return;
        // The release position counts even if its frame hasn't run yet.
        if (pendingMove.current) dragTo(pendingMove.current);
        latest.current.onCommit(current.selection);
        endDrag(event);
      },

      onPointerCancel: (event) => {
        if (!drag.current || drag.current.pointerId !== event.pointerId) return;
        latest.current.onDiscard();
        endDrag(event);
      },

      onPointerLeave: () => {
        if (drag.current) return;
        cancelAnimationFrame(frame.current);
        frame.current = 0;
        pendingMove.current = null;
        setHoveredHandle(null);
        latest.current.onHover(null);
      },

      onKeyDown: (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        const { durationMs, selection, onCommit } = latest.current;
        if (drag.current || durationMs <= 0) return;
        event.preventDefault();
        const step =
          (event.shiftKey ? KEY_STEP_LARGE_MS : KEY_STEP_MS) * (event.key === "ArrowLeft" ? -1 : 1);
        onCommit(
          centredSelection((selection?.point ?? 0) + step, currentHalfWidth(selection), durationMs),
        );
      },
    };
  }, []);

  return { handlers, activeHandle, hoveredHandle };
}
