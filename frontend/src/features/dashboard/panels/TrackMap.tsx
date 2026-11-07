import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import { useRunPositions } from "@features/dashboard/data/useDashboardData";
import { useHoverTimeSubscription } from "@features/dashboard/state/useDashboard";
import {
  anchorAt,
  distanceAt,
  gapPath,
  headingAt,
  makeTrack,
  nearestSample,
  positionAt,
  tickAt,
  trackPath,
  windowPath,
} from "@features/dashboard/utils/trackmap";
import { cx } from "@utils/classNames";
import { TrackVisualization, type DragMode } from "./TrackVisualization";
import {
  clampHalf,
  selectionWindow,
  useTrackSelection,
  type TrackSelection,
} from "./useTrackSelection";
import styles from "./TrackMap.module.css";

// Half the length of the lines across the track, in SVG units (longer side 100):
// the start line, and the longer bars that are the window's resize handles.
const TICK_HALF_LENGTH = 2.6;
const HANDLE_HALF_LENGTH = 3.4;
// How close (screen px) a press must be to the road to move the car there.
const ROAD_HIT_PX = 14;
// The car's grab circle, in SVG units: this big when the handles are far away,
// shrinking with a short window so it never covers them, but never below the min.
const CAR_HIT_RADIUS = 4.5;
const CAR_HIT_MIN_RADIUS = 0.8;

type Drag = {
  mode: DragMode;
  // The pointer that started the drag; other pointers (a second finger) are ignored.
  pointerId: number;
  // Which edge is held: -1 the start, +1 the end. Mutated in place by the move
  // handler when the edge is dragged past the car and becomes the other one.
  side: -1 | 1;
  // The selection before the drag, restored on Esc.
  before: TrackSelection;
};

const clamp = (v: number, lo: number, hi: number) => Math.min(Math.max(v, lo), hi);

// The pointer in SVG units: track points are in viewBox units, not screen pixels.
function toSvgPoint(svg: SVGSVGElement, e: ReactPointerEvent) {
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
  return { x: p.x, y: p.y, unitsPerPx: 1 / ctm.a };
}

// The car sits at the window's centre: drag it to slide the window along the run;
// drag either white handle to resize the window, by the same distance of road on
// both sides of the car.
// A drag only redraws the map; the window is committed (and other panels update)
// on release.
export function TrackMap() {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const ghostRef = useRef<SVGCircleElement | null>(null);
  const dragRef = useRef<Drag | null>(null);
  const [dragMode, setDragMode] = useState<DragMode | null>(null);

  const {
    positions,
    positionsIsLoading: isLoading,
    positionsIsPlaceholderData: isPlaceholderData,
    positionsError: error,
  } = useRunPositions("overview");

  const track = useMemo(
    () =>
      positions && positions.time.length > 0
        ? makeTrack(positions.positions, positions.time, positions.startMs)
        : null,
    [positions],
  );
  const { selection, selectionRef, update, commit, applied } = useTrackSelection(track);

  // Static layers, once per track.
  const base = useMemo(() => {
    if (!track) return null;
    return {
      road: trackPath(track),
      gaps: gapPath(track),
      start: tickAt(track, anchorAt(track, track.firstTime), TICK_HALF_LENGTH),
    };
  }, [track]);

  // The selection's layers, on every drag move.
  const shape = useMemo(() => {
    if (!track || !selection) return null;
    const [from, to] = selectionWindow(track, selection);
    const ends = [anchorAt(track, from), anchorAt(track, to)] as const;
    const car = anchorAt(track, selection.center);
    // At most half the way to the nearer handle, so a press between them goes to
    // whichever is closer and a short window can still be resized.
    const nearest = Math.min(...ends.map((end) => Math.hypot(end.x - car.x, end.y - car.y)));
    return {
      window: windowPath(track, from, to),
      car: {
        x: car.x,
        y: car.y,
        heading: headingAt(track, car),
        hitRadius: clamp(nearest / 2, CAR_HIT_MIN_RADIUS, CAR_HIT_RADIUS),
      },
      edges: [
        tickAt(track, ends[0], HANDLE_HALF_LENGTH),
        tickAt(track, ends[1], HANDLE_HALF_LENGTH),
      ] as const,
    };
  }, [track, selection]);

  // Hover from other panels (charts) shows as a faint ghost marker. Moved
  // directly, not through React state, so the map doesn't re-render per frame.
  useHoverTimeSubscription((t) => {
    const ghost = ghostRef.current;
    if (!ghost || !track) return;
    const pos = positionAt(track, t);
    ghost.setAttribute("visibility", pos ? "visible" : "hidden");
    if (pos) {
      ghost.setAttribute("cx", String(pos.x));
      ghost.setAttribute("cy", String(pos.y));
    }
  });

  const endDrag = useCallback(() => {
    dragRef.current = null;
    setDragMode(null);
  }, []);

  const cancelDrag = useCallback(() => {
    const drag = dragRef.current;
    if (!drag) return;
    endDrag();
    update(drag.before);
  }, [update, endDrag]);

  // Release: commit the window. Also reached if the pointer is lost or released
  // without a pointerup, so a drag can never get stuck following the pointer.
  const finishDrag = useCallback(() => {
    if (!dragRef.current) return;
    endDrag();
    commit();
  }, [commit, endDrag]);

  // Pointer events end or cancel the drag only for the pointer that started it.
  const isDragPointer = (e: ReactPointerEvent) => dragRef.current?.pointerId === e.pointerId;
  const handlePointerUp = (e: ReactPointerEvent<SVGSVGElement>) => {
    if (isDragPointer(e)) finishDrag();
  };
  const handlePointerCancel = (e: ReactPointerEvent<SVGSVGElement>) => {
    if (isDragPointer(e)) cancelDrag();
  };

  // Esc abandons the drag and puts the window back where it was.
  useEffect(() => {
    if (!dragMode) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") cancelDrag();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dragMode, cancelDrag]);

  const handlePointerDown = useCallback(
    (e: ReactPointerEvent<SVGSVGElement>) => {
      const svg = svgRef.current;
      const current = selectionRef.current;
      if (!svg || !track || !current || dragRef.current) return;
      if (!e.isPrimary || e.button !== 0) return;
      const p = toSvgPoint(svg, e);
      if (!p) return;

      const role = (e.target as Element).closest("[data-handle]")?.getAttribute("data-handle");
      const start = { pointerId: e.pointerId, before: current };
      let drag: Drag;
      if (role === "car") {
        drag = { ...start, mode: "car", side: 1 };
      } else if (role === "start" || role === "end") {
        drag = { ...start, mode: "edge", side: role === "start" ? -1 : 1 };
      } else {
        // A press on the road moves the car there; a press on empty space does
        // nothing. Only passes under the pointer count, and of those the one
        // nearest in time to the car wins, so any pass of the road can be picked
        // (an out-lap or the pit lane too, however long ago it was driven).
        const hit = nearestSample(track, p.x, p.y, current.center, ROAD_HIT_PX * p.unitsPerPx);
        if (!hit) return;
        drag = { ...start, mode: "car", side: 1 };
        update({ ...current, center: hit.time });
      }

      e.preventDefault();
      try {
        // Keep receiving moves when the pointer leaves the map mid-drag.
        svg.setPointerCapture(e.pointerId);
      } catch {
        // The pointer is already gone; the drag still works while it's over the map.
      }
      dragRef.current = drag;
      setDragMode(drag.mode);
    },
    [track, selectionRef, update],
  );

  const handlePointerMove = useCallback(
    (e: ReactPointerEvent<SVGSVGElement>) => {
      const drag = dragRef.current;
      const svg = svgRef.current;
      const current = selectionRef.current;
      if (!drag || !svg || !track || !current || e.pointerId !== drag.pointerId) return;
      // The button came up without a pointerup reaching us: treat it as release.
      if (e.buttons === 0) {
        finishDrag();
        return;
      }
      const p = toSvgPoint(svg, e);
      if (!p) return;

      if (drag.mode === "car") {
        const hit = nearestSample(track, p.x, p.y, current.center);
        if (hit && hit.time !== current.center) update({ ...current, center: hit.time });
        return;
      }
      // Edge: the held edge follows the pointer; the other mirrors it around the
      // car by the same distance of road.
      const edge = selectionWindow(track, current)[drag.side < 0 ? 0 : 1];
      const hit = nearestSample(track, p.x, p.y, edge);
      if (!hit) return;
      const offset = distanceAt(track, hit.time) - distanceAt(track, current.center);
      if (offset !== 0) drag.side = offset < 0 ? -1 : 1;
      const halfM = clampHalf(track, Math.abs(offset));
      if (halfM !== current.halfM) update({ ...current, halfM });
    },
    [track, selectionRef, update, finishDrag],
  );

  if (isLoading) return <LoadingState message="Loading track…" />;
  if (error) return <ErrorState error={error} />;
  if (!track || !base || !shape || !selection) {
    return <EmptyState message="No position data for this run." />;
  }

  return (
    // Placeholder data is the previous request's, shown while new data loads: dim
    // it so it reads as out of date. (The "overview" scope never changes request
    // within a run, so this only matters if the map moves to "detail".)
    <div className={cx(styles.container, isPlaceholderData && styles.stale)}>
      <TrackVisualization
        svgRef={svgRef}
        ghostRef={ghostRef}
        viewSize={track.viewSize}
        road={base.road}
        gaps={base.gaps}
        start={base.start}
        window={shape.window}
        car={shape.car}
        edges={shape.edges}
        pending={!applied && !dragMode}
        dragMode={dragMode}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onLostPointerCapture={handlePointerUp}
      />

      <p className={styles.hint}>
        {applied
          ? "Drag the car to move the window · drag a handle to resize · Esc cancels"
          : "Drag the car or click the track to select a window"}
      </p>
    </div>
  );
}
