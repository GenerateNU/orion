// TrackMap.tsx
import { useState, useMemo, useRef, useCallback } from "react";
import {
  useCommittedWindow,
  useDashboardActions,
  useHoverTimeSubscription,
} from "@features/dashboard/state/useDashboard";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import { useRunPositions } from "@features/dashboard/data/useDashboardData";
import {
  getTimeFromMouse,
  getCarPosition,
  generateSegments,
  getMousePosOnSVG,
  makeTrack,
  trackPoints,
} from "@features/dashboard/utils/trackmap";
import { TrackVisualization } from "./TrackVisualization";
import styles from "@features/dashboard/TrackMap.module.css";
import { cx } from "@utils/classNames";

export function TrackMap() {
  const stageRef = useRef<SVGSVGElement | null>(null);
  const carRef = useRef<SVGCircleElement | null>(null);
  // Drag ends in RunTime (ms since the run's start), like every dashboard window.
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);

  const {
    previewWindow,
    commitWindow,
    setHoverTime: setDashboardHoverTime,
  } = useDashboardActions();
  const committedWindow = useCommittedWindow();

  const {
    positions,
    positionsIsLoading: isLoading,
    positionsIsPlaceholderData: isPlaceholderData,
    positionsError: error,
  } = useRunPositions("overview");

  // The helpers read the cached arrays in place (no copies) and work in their
  // unit, epoch ms. Convert RunTime <-> epoch ms only where a time crosses over:
  //   RunTime = epoch - startMs
  const startMs = positions?.startMs ?? 0;
  const track = useMemo(
    () =>
      positions && positions.time.length > 0
        ? makeTrack(positions.positions, positions.time)
        : null,
    [positions],
  );
  const points = useMemo(() => (track ? trackPoints(track) : ""), [track]);

  // Hover changes come from any panel, up to once a frame. Move the marker
  // directly instead of through React state, so the map doesn't re-render.
  useHoverTimeSubscription((t) => {
    const car = carRef.current;
    if (!car || !track) return;
    const pos = getCarPosition(track, t === null ? null : t + startMs);
    if (!pos) {
      car.setAttribute("visibility", "hidden");
      return;
    }
    car.setAttribute("cx", String(pos.x));
    car.setAttribute("cy", String(pos.y));
    car.setAttribute("visibility", "visible");
  });

  // Hidden while a new drag is in progress, so only the new selection shows.
  const isDragging = dragStart !== null;
  const committedSegments = useMemo(() => {
    if (isDragging || !committedWindow || !track) return [];
    return generateSegments(track, committedWindow[0] + startMs, committedWindow[1] + startMs);
  }, [isDragging, committedWindow, track, startMs]);

  const previewSegments = useMemo(() => {
    if (dragStart === null || dragEnd === null || !track) return [];
    const start = Math.min(dragStart, dragEnd);
    const end = Math.max(dragStart, dragEnd);
    return generateSegments(track, start + startMs, end + startMs);
  }, [dragStart, dragEnd, track, startMs]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!track) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      const timeVal = getTimeFromMouse(track, pos.x, pos.y) - startMs;
      setDragStart(timeVal);
      setDragEnd(timeVal);
    },
    [track, startMs],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!track) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      // While dragging, stay on the lap the drag is following (see getTimeFromMouse).
      const nearTime = dragEnd === null ? undefined : dragEnd + startMs;
      const timeVal = getTimeFromMouse(track, pos.x, pos.y, nearTime) - startMs;

      if (dragStart === null) {
        setDashboardHoverTime(timeVal);
      } else {
        setDragEnd(timeVal);
        const [start, end] = dragStart < timeVal ? [dragStart, timeVal] : [timeVal, dragStart];
        previewWindow([start, end]);
      }
    },
    [dragStart, dragEnd, track, startMs, setDashboardHoverTime, previewWindow],
  );

  const handleMouseUp = useCallback(() => {
    if (dragStart === null || dragEnd === null) return;
    const [start, end] = dragStart < dragEnd ? [dragStart, dragEnd] : [dragEnd, dragStart];
    commitWindow([start, end]);
    setDragStart(null);
    setDragEnd(null);
  }, [dragStart, dragEnd, commitWindow]);

  const handleMouseLeave = useCallback(() => {
    setDragStart(null);
    setDragEnd(null);
  }, []);

  if (isLoading) return <LoadingState message="Loading track…" />;
  if (error) return <ErrorState error={error} />;
  if (!track) return <EmptyState message="No position data for this run." />;

  return (
    // Placeholder data is the previous request's, shown while new data loads:
    // dim it so it reads as out of date. (The "overview" scope never changes
    // request within a run, so this only matters if the map moves to "detail".)
    <div className={cx(styles.container, isPlaceholderData && styles.stale)}>
      <TrackVisualization
        points={points}
        committedSegments={committedSegments}
        previewSegments={previewSegments}
        carRef={carRef}
        viewSize={track.viewSize}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        stageRef={stageRef}
      />
    </div>
  );
}
