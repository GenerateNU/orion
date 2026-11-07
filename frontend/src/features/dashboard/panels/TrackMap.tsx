import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import { useRunPositions } from "@features/dashboard/data/useDashboardData";
import { useHoverTimeSubscription } from "@features/dashboard/state/useDashboard";
import {
  anchorAt,
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
import { formatDuration } from "@utils/format";
import { TrackVisualization, type DragMode } from "./TrackVisualization";
import {
  MIN_HALF_MS,
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

type Drag = {
  mode: DragMode;
  // Which edge is held: -1 the start, +1 the end (flips if dragged past the car).
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
// drag either white handle to resize the window symmetrically around the car.
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
    const [from, to] = selectionWindow(selection);
    const handle = (t: number) => tickAt(track, anchorAt(track, t), HANDLE_HALF_LENGTH);
    const car = anchorAt(track, selection.center);
    return {
      window: windowPath(track, from, to),
      car: { x: car.x, y: car.y, heading: headingAt(track, car) },
      edges: [handle(from), handle(to)] as const,
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
      if (!svg || !track || !current || !e.isPrimary || e.button !== 0) return;
      const p = toSvgPoint(svg, e);
      if (!p) return;

      const role = (e.target as Element).closest("[data-handle]")?.getAttribute("data-handle");
      let drag: Drag;
      if (role === "car") {
        drag = { mode: "car", side: 1, before: current };
      } else if (role === "start" || role === "end") {
        drag = { mode: "edge", side: role === "start" ? -1 : 1, before: current };
      } else {
        // A press on the road moves the car there (preferring the pass nearest in
        // time to where it is now); a press on empty space does nothing.
        const hit = nearestSample(track, p.x, p.y, current.center);
        if (!hit || hit.dist > ROAD_HIT_PX * p.unitsPerPx) return;
        drag = { mode: "car", side: 1, before: current };
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
      if (!drag || !svg || !track || !current) return;
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
      // Edge: the held edge follows the pointer; the other mirrors it around the car.
      const edge = current.center + drag.side * current.half;
      const hit = nearestSample(track, p.x, p.y, edge);
      if (!hit) return;
      const offset = hit.time - current.center;
      if (offset !== 0) drag.side = offset < 0 ? -1 : 1;
      const maxHalf = Math.max(MIN_HALF_MS, (track.lastTime - track.firstTime) / 2);
      const half = clamp(Math.abs(offset), MIN_HALF_MS, maxHalf);
      if (half !== current.half) update({ ...current, half });
    },
    [track, selectionRef, update, finishDrag],
  );

  if (isLoading) return <LoadingState message="Loading track…" />;
  if (error) return <ErrorState error={error} />;
  if (!track || !base || !shape || !selection) {
    return <EmptyState message="No position data for this run." />;
  }

  const [from, to] = selectionWindow(selection);
  const clock = (ms: number) => formatDuration(clamp(ms, 0, track.lastTime) / 1000);

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
        onPointerUp={finishDrag}
        onPointerCancel={cancelDrag}
        onLostPointerCapture={finishDrag}
      />

      <dl className={styles.readout}>
        <div className={styles.stat}>
          <dt>Car</dt>
          <dd>{clock(selection.center)}</dd>
        </div>
        <div className={styles.stat}>
          <dt>Window</dt>
          <dd>
            {clock(from)} – {clock(to)}
          </dd>
        </div>
        <div className={styles.stat}>
          <dt>Width</dt>
          <dd>{Math.round((selection.half * 2) / 1000)} s</dd>
        </div>
      </dl>
      <p className={styles.hint}>
        {applied
          ? "Drag the car to move the window · drag a handle to resize · Esc cancels"
          : "Drag the car or click the track to select a window"}
      </p>
    </div>
  );
}
