import { useState, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "@tanstack/react-router";
import {
  useCommittedWindow,
  useDashboardActions,
  useHoverTimeSubscription,
} from "../state/useDashboard";
import EmptyState from "../../../components/ui/EmptyState";
import {
  getTimeFromMouse,
  getCarPosition,
  generateSegments,
  type Position,
} from "../utils/trackmap";
import styles from "../TrackMap.module.css";

interface CarState {
  time: string;
  lattitude: number;
  longitude: number;
}

export function TrackMap() {
  const { runId } = useParams({ from: "/runs/$runId/dashboard" });
  const stageRef = useRef<SVGSVGElement>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);

  const {
    previewWindow,
    commitWindow,
    setHoverTime: setDashboardHoverTime,
  } = useDashboardActions();
  const committedWindow = useCommittedWindow();

  // Fetch real position data from backend
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
      // Map API response to CarState[]
      return (
        json.positions.map((pos: [number, number], i: number) => ({
          time: json.time[i],
          lattitude: pos[1], // lat is second element
          longitude: pos[0], // lon is first element
        })) || []
      );
    },
  });

  // Convert lat/lon to SVG coords
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

    // Extract positions as [x, y] tuples and times (convert ISO to microseconds)
    const positions: Position[] = svgPts.map((p: { x: unknown; y: unknown }) => [p.x, p.y]);
    const times = states.map((s: CarState) => {
      const date = new Date(s.time);
      return date.getTime() * 1000; // Convert to microseconds
    });

    return { svgPoints: svgPts, positions, time: times };
  }, [states]);

  // Listen for hover time from other panels
  useHoverTimeSubscription((t) => {
    setHoverTime(t);
  });

  console.log("committedWindow:", committedWindow);
  console.log("time array sample:", time.slice(0, 3));

  // Generate committed window segments
  const committedSegments = useMemo(() => {
    if (!committedWindow || time.length === 0) return [];
    return generateSegments(committedWindow[0], committedWindow[1], positions, time);
  }, [committedWindow, positions, time]);

  // Generate preview window segments (while dragging)
  const previewSegments = useMemo(() => {
    if (dragStart === null || dragEnd === null || time.length === 0) return [];
    const start = Math.min(dragStart, dragEnd);
    const end = Math.max(dragStart, dragEnd);
    return generateSegments(start, end, positions, time);
  }, [dragStart, dragEnd, positions, time]);

  const carPos = getCarPosition(hoverTime, positions, time);

  // Mouse event handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!stageRef.current || time.length === 0) return;
    const rect = stageRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const timeVal = getTimeFromMouse(positions, time, mouseX, mouseY);
    setDragStart(timeVal);
    setDragEnd(timeVal);
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!stageRef.current || time.length === 0) return;
    const rect = stageRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const timeVal = getTimeFromMouse(positions, time, mouseX, mouseY);

    if (dragStart === null) {
      // Not dragging, just update hover time
      setDashboardHoverTime(timeVal);
    } else {
      // Dragging, update preview
      setDragEnd(timeVal);
      const [start, end] = dragStart < timeVal ? [dragStart, timeVal] : [timeVal, dragStart];
      previewWindow([start, end]);
    }
  };

  const handleMouseUp = () => {
    if (dragStart === null || dragEnd === null) return;
    const [start, end] = dragStart < dragEnd ? [dragStart, dragEnd] : [dragEnd, dragStart];
    commitWindow([start, end]);
    setDragStart(null);
    setDragEnd(null);
  };

  const handleMouseLeave = () => {
    setDragStart(null);
    setDragEnd(null);
  };

  console.log("isLoading:", isLoading, "error:", error, "svgPoints.length:", svgPoints.length);

  if (isLoading) return <EmptyState message="Loading track..." />;
  if (error || svgPoints.length === 0) {
    return <EmptyState message="No position data available" />;
  }

  console.log("svgPoints length:", svgPoints.length);
  console.log("svgPoints sample:", svgPoints.slice(0, 3));

  const polylinePoints = svgPoints
    .map((p: { x: unknown; y: unknown }) => `${p.x},${p.y}`)
    .join(" ");
  console.log("polylinePoints:", polylinePoints.slice(0, 100));

  return (
    <div className={styles.container}>
      <svg
        ref={stageRef}
        width={400}
        height={300}
        className={styles.stage}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      >
        {/* Track polyline */}
        <polyline
          points={svgPoints.map((p: { x: unknown; y: unknown }) => `${p.x},${p.y}`).join(" ")}
          stroke="var(--text-secondary)"
          strokeWidth="3"
          fill="none"
        />

        {/* Committed window lines */}
        {committedSegments.map((seg, i) => (
          <line
            key={`committed-${i}`}
            x1={seg.x1}
            y1={seg.y1}
            x2={seg.x2}
            y2={seg.y2}
            stroke="red"
            strokeWidth="3"
          />
        ))}

        {/* Preview window lines */}
        {previewSegments.map((seg, i) => (
          <line
            key={`preview-${i}`}
            x1={seg.x1}
            y1={seg.y1}
            x2={seg.x2}
            y2={seg.y2}
            stroke="yellow"
            strokeWidth="2"
            opacity="0.7"
          />
        ))}

        {/* Car dot */}
        {carPos && <circle cx={carPos.x} cy={carPos.y} r="6" fill="white" />}
      </svg>

      {committedWindow && (
        <p className={styles.info}>
          {Math.round(committedWindow[0] / 1000000)}–{Math.round(committedWindow[1] / 1000000)}s
        </p>
      )}
    </div>
  );
}
