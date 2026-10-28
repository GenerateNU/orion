import { useState, useMemo, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import {
  useCommittedWindow,
  useDashboardActions,
  useHoverTimeSubscription,
} from "@features/dashboard/state/useDashboard";
import EmptyState from "@components/ui/EmptyState";
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
  time: string;
  lattitude: number;
  longitude: number;
}

export function TrackMap() {
  const { runId } = useParams({ from: "/runs/$runId/dashboard" });
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
    data: states = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["state", runId],
    queryFn: async () => {
      const start = new Date("2026-10-28T12:00:00Z").toISOString();
      const end = new Date("2026-10-28T12:01:00Z").toISOString();
      const res = await fetch(`/api/v1/runs/${runId}/state?start=${start}&end=${end}`);
      if (!res.ok) throw new Error("Failed to fetch state");
      const json = await res.json();
      return (
        json.positions.map((pos: [number, number], i: number) => ({
          time: json.time[i],
          lattitude: pos[1],
          longitude: pos[0],
        })) || []
      );
    },
  });

  const { svgPoints, positions, time } = useMemo(() => {
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
    }));

    const positions: Position[] = svgPts.map((p: { x: unknown; y: unknown }) => [p.x, p.y]);
    const times = states.map((s: CarState) => {
      const date = new Date(s.time);
      return date.getTime() * 1000;
    });

    return { svgPoints: svgPts, positions, time: times };
  }, [states]);

  useHoverTimeSubscription((t) => {
    setHoverTime(t);
  });

  const committedSegments = useMemo(() => {
    if (!committedWindow || time.length === 0) return [];
    return generateSegments(committedWindow[0], committedWindow[1], positions, time);
  }, [committedWindow, positions, time]);

  const previewSegments = useMemo(() => {
    if (dragStart === null || dragEnd === null || time.length === 0) return [];
    const start = Math.min(dragStart, dragEnd);
    const end = Math.max(dragStart, dragEnd);
    return generateSegments(start, end, positions, time);
  }, [dragStart, dragEnd, positions, time]);

  const carPos = getCarPosition(hoverTime, positions, time);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (time.length === 0) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      const timeVal = getTimeFromMouse(positions, time, pos.x, pos.y);
      setDragStart(timeVal);
      setDragEnd(timeVal);
    },
    [positions, time],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (time.length === 0) return;
      const pos = getMousePosOnSVG(e, stageRef);
      if (!pos) return;
      const timeVal = getTimeFromMouse(positions, time, pos.x, pos.y);

      if (dragStart === null) {
        setDashboardHoverTime(timeVal);
      } else {
        setDragEnd(timeVal);
        const [start, end] = dragStart < timeVal ? [dragStart, timeVal] : [timeVal, dragStart];
        previewWindow([start, end]);
      }
    },
    [dragStart, positions, time, setDashboardHoverTime, previewWindow],
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
