import { useState, useMemo, useRef, useCallback } from "react";
import {
  useCommittedWindow,
  useDashboardActions,
  useHoverTimeSubscription,
} from "@features/dashboard/state/useDashboard";
import EmptyState from "@components/ui/EmptyState";
import { useRunPositions } from "@features/dashboard/data/useDashboardData";
import {
  getTimeFromMouse,
  getCarPosition,
  generateSegments,
  getMousePosOnSVG,
  type Position,
} from "@features/dashboard/utils/trackmap";
import { TrackVisualization } from "./TrackVisualization";
import styles from "@features/dashboard/TrackMap.module.css";

interface CarState {
  time: number;
  lattitude: number;
  longitude: number;
}

export function TrackMap() {
  const stageRef = useRef<SVGSVGElement | null>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
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
    positionsError: error,
  } = useRunPositions("overview");

  const states = useMemo(() => {
    if (!positions) return [];
    return positions.positions.map((pos: [number, number], i: number) => ({
      time: positions.time[i],
      lattitude: pos[1],
      longitude: pos[0],
    }));
  }, [positions]);

  const {
    svgPoints,
    positions: svgPositions,
    time,
  } = useMemo(() => {
    if (states.length === 0) return { svgPoints: [], positions: [], time: [] };

    const lats = states.map((s: CarState) => s.lattitude);
    const lons = states.map((s: CarState) => s.longitude);

    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);

    const width = 400;
    const height = 300;
    const padding = 20;

    const svgPts = states.map((s: CarState) => ({
      x: padding + ((s.longitude - minLon) / (maxLon - minLon || 1)) * (width - 2 * padding),
      y: padding + ((s.lattitude - minLat) / (maxLat - minLat || 1)) * (height - 2 * padding),
    })) as Array<{ x: number; y: number }>;

    const svgPositions: Position[] = svgPts.map((p) => [p.x, p.y]);
    const times = states.map((s: CarState) => s.time * 1000);

    return { svgPoints: svgPts, positions: svgPositions, time: times };
  }, [states]);

  useHoverTimeSubscription((t) => {
    setHoverTime(t);
  });

  const committedSegments = useMemo(() => {
    if (!committedWindow || time.length === 0) return [];
    return generateSegments(committedWindow[0], committedWindow[1], svgPositions, time);
  }, [committedWindow, svgPositions, time]);

  const previewSegments = useMemo(() => {
    if (dragStart === null || dragEnd === null || time.length === 0) return [];
    const start = Math.min(dragStart, dragEnd);
    const end = Math.max(dragStart, dragEnd);
    return generateSegments(start, end, svgPositions, time);
  }, [dragStart, dragEnd, svgPositions, time]);

  const carPos = getCarPosition(hoverTime, svgPositions, time);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (time.length === 0) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      const timeVal = getTimeFromMouse(svgPositions, time, pos.x, pos.y);
      setDragStart(timeVal);
      setDragEnd(timeVal);
    },
    [svgPositions, time],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (time.length === 0) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      const timeVal = getTimeFromMouse(svgPositions, time, pos.x, pos.y);

      if (dragStart === null) {
        setDashboardHoverTime(timeVal);
      } else {
        setDragEnd(timeVal);
        const [start, end] = dragStart < timeVal ? [dragStart, timeVal] : [timeVal, dragStart];
        previewWindow([start, end]);
      }
    },
    [dragStart, svgPositions, time, setDashboardHoverTime, previewWindow],
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

  if (isLoading) return <EmptyState message="Loading track..." />;
  if (error || svgPoints.length === 0) {
    return <EmptyState message="No position data available" />;
  }

  return (
    <div className={styles.container}>
      <TrackVisualization
        svgPoints={svgPoints}
        committedSegments={committedSegments}
        previewSegments={previewSegments}
        carPos={carPos}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        stageRef={stageRef}
      />
    </div>
  );
}
