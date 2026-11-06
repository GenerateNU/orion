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
  getMousePosOnSVG,
  makeTrack,
  startFinishTick,
  tickAt,
  trackPoints,
  windowPoints,
  type Tick,
} from "@features/dashboard/utils/trackmap";
import { TrackVisualization } from "./TrackVisualization";
import styles from "@features/dashboard/TrackMap.module.css";
import { cx } from "@utils/classNames";
import type { TimeWindow } from "@features/dashboard/utils/time";

// Half the length of the lines across the track, in SVG units (the drawing's
// longer side is 100).
const TICK_HALF_LENGTH = 3;

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

  // Every time here is RunTime; the trackmap helpers convert to the cached
  // array's epoch ms themselves, using the run's start stored on the track.
  const track = useMemo(
    () =>
      positions && positions.time.length > 0
        ? makeTrack(positions.positions, positions.time, positions.startMs)
        : null,
    [positions],
  );
  const points = useMemo(() => (track ? trackPoints(track) : ""), [track]);

  // Hover changes come from any panel, up to once a frame. Move the marker
  // directly instead of through React state, so the map doesn't re-render.
  useHoverTimeSubscription((t) => {
    const car = carRef.current;
    if (!car || !track) return;
    const pos = getCarPosition(track, t);
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
  const dragWindow = useMemo(
    (): TimeWindow | null =>
      dragStart === null || dragEnd === null
        ? null
        : [Math.min(dragStart, dragEnd), Math.max(dragStart, dragEnd)],
    [dragStart, dragEnd],
  );
  const shownWindow = isDragging ? dragWindow : committedWindow;

  const committedPoints = useMemo(() => {
    if (isDragging || !committedWindow || !track) return "";
    return windowPoints(track, committedWindow[0], committedWindow[1]);
  }, [isDragging, committedWindow, track]);

  const previewPoints = useMemo(() => {
    if (!dragWindow || !track) return "";
    return windowPoints(track, dragWindow[0], dragWindow[1]);
  }, [dragWindow, track]);

  // Lines across the track at the shown window's edges, and at the run's start
  // (the start/finish line, since a run starts there).
  const windowTicks = useMemo((): Tick[] => {
    if (!shownWindow || !track) return [];
    return shownWindow
      .map((t) => tickAt(track, t, TICK_HALF_LENGTH))
      .filter((tick): tick is Tick => tick !== null);
  }, [shownWindow, track]);
  const startFinish = useMemo(
    () => (track ? startFinishTick(track, TICK_HALF_LENGTH) : null),
    [track],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!track) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      const timeVal = getTimeFromMouse(track, pos.x, pos.y);
      setDragStart(timeVal);
      setDragEnd(timeVal);
    },
    [track],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!track) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      // While dragging, stay on the lap the drag is following (see getTimeFromMouse).
      const timeVal = getTimeFromMouse(track, pos.x, pos.y, dragEnd ?? undefined);

      if (dragStart === null) {
        setDashboardHoverTime(timeVal);
      } else {
        setDragEnd(timeVal);
        const [start, end] = dragStart < timeVal ? [dragStart, timeVal] : [timeVal, dragStart];
        previewWindow([start, end]);
      }
    },
    [dragStart, dragEnd, track, setDashboardHoverTime, previewWindow],
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
        committedPoints={committedPoints}
        previewPoints={previewPoints}
        windowTicks={windowTicks}
        startFinish={startFinish}
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
