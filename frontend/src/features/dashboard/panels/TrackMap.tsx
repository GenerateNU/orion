import { useState, useMemo, useRef } from "react";
import { Stage, Layer, Path, Circle, Line } from "react-konva";
import {
  useCommittedWindow,
  useDashboardActions,
  useHoverTimeSubscription,
} from "../state/useDashboard";
import { useMockPositions, formatTime } from "../panels/useMockPositions";
import EmptyState from "../../../components/ui/EmptyState";

export function TrackMap() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stageRef = useRef<any>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const {
    previewWindow,
    commitWindow,
    setHoverTime: setDashboardHoverTime,
  } = useDashboardActions();
  const committedWindow = useCommittedWindow();

  // Get mock position (now x,y) and time data
  const { time, positions } = useMockPositions();

  // Listen for hover time from other panels
  useHoverTimeSubscription((t) => {
    setHoverTime(t);
  });

  // Convert mouse position to time based on closest track point
  const getTimeFromMouse = () => {
    if (!stageRef.current) return 0;
    const pointerPos = stageRef.current.getPointerPosition();
    if (!pointerPos) return 0;

    const mouseX = pointerPos.x;
    const mouseY = pointerPos.y;

    // Find closest point on track
    let minDist = Infinity;
    let closestIdx = 0;

    for (let i = 0; i < positions.length; i++) {
      const [x, y] = positions[i];
      const dist = Math.hypot(mouseX - x, mouseY - y);
      if (dist < minDist) {
        minDist = dist;
        closestIdx = i;
      }
    }

    // Interpolate time at closest index
    if (closestIdx === positions.length - 1) {
      return time[closestIdx];
    }

    // Simple linear interpolation between closest points
    const t = Math.min(1, minDist / 20); // Interpolate within 20px
    return time[closestIdx] + (time[closestIdx + 1] - time[closestIdx]) * t;
  };

  // Get car position by interpolating x,y directly
  const getCarPosition = (hoverTimeVal: number | null) => {
    if (hoverTimeVal === null) return null;

    // Find the two closest time points
    let idx = 0;
    for (let i = 0; i < time.length; i++) {
      if (time[i] <= hoverTimeVal) idx = i;
      else break;
    }

    if (idx === time.length - 1) {
      // At or past the end
      const [x, y] = positions[idx];
      return { x, y };
    }

    // Interpolate between idx and idx+1
    const t0 = time[idx];
    const t1 = time[idx + 1];
    const [x0, y0] = positions[idx];
    const [x1, y1] = positions[idx + 1];

    // Linear interpolation factor
    const factor = (hoverTimeVal - t0) / (t1 - t0);
    const x = x0 + (x1 - x0) * factor;
    const y = y0 + (y1 - y0) * factor;

    return { x, y };
  };

  // Generate track path from x,y positions
  const trackPath = useMemo(() => {
    if (!positions || positions.length === 0) return "";

    let pathData = `M ${positions[0][0]} ${positions[0][1]}`;
    for (let i = 1; i < positions.length; i++) {
      pathData += ` L ${positions[i][0]} ${positions[i][1]}`;
    }
    // Close the path
    pathData += ` L ${positions[0][0]} ${positions[0][1]}`;
    return pathData;
  }, [positions]);

  // Generate committed window line segments
  const committedSegments = useMemo(() => {
    if (!committedWindow) return [];

    // committedWindow is in microseconds, time array is also in microseconds
    const startIdx = Math.round(
      (committedWindow[0] / time[time.length - 1]) * (positions.length - 1),
    );
    const endIdx = Math.round(
      (committedWindow[1] / time[time.length - 1]) * (positions.length - 1),
    );

    const segments: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];

    for (let i = startIdx; i < endIdx && i < positions.length - 1; i++) {
      const [x1, y1] = positions[i];
      const [x2, y2] = positions[i + 1];
      segments.push({ x1, y1, x2, y2 });
    }

    return segments;
  }, [committedWindow, positions, time]);

  // Generate preview window line segments (while dragging)
  const previewSegments = useMemo(() => {
    if (dragStart === null || dragEnd === null) return [];

    const start = Math.min(dragStart, dragEnd);
    const end = Math.max(dragStart, dragEnd);

    const startIdx = Math.round((start / time[time.length - 1]) * (positions.length - 1));
    const endIdx = Math.round((end / time[time.length - 1]) * (positions.length - 1));

    const segments: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];

    for (let i = startIdx; i < endIdx && i < positions.length - 1; i++) {
      const [x1, y1] = positions[i];
      const [x2, y2] = positions[i + 1];
      segments.push({ x1, y1, x2, y2 });
    }

    return segments;
  }, [dragStart, dragEnd, positions, time]);

  const carPos = getCarPosition(hoverTime);

  if (!positions || positions.length === 0) {
    return <EmptyState message="No position data available" />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <Stage
        ref={stageRef}
        width={400}
        height={300}
        style={{
          backgroundColor: "var(--bg-dark)",
          cursor: dragStart !== null ? "grabbing" : "grab",
        }}
        onMouseDown={() => {
          const timeVal = getTimeFromMouse();
          setDragStart(timeVal);
          setDragEnd(timeVal);
        }}
        onMouseMove={() => {
          if (dragStart === null) {
            // Not dragging, just update hover time
            const timeVal = getTimeFromMouse();
            setDashboardHoverTime(timeVal);
          } else {
            // Dragging, update preview
            const timeVal = getTimeFromMouse();
            setDragEnd(timeVal);
            const [start, end] = dragStart < timeVal ? [dragStart, timeVal] : [timeVal, dragStart];
            previewWindow([start, end]);
          }
        }}
        onMouseUp={() => {
          if (dragStart === null || dragEnd === null) return;
          const [start, end] = dragStart < dragEnd ? [dragStart, dragEnd] : [dragEnd, dragStart];
          commitWindow([start, end]);
          setDragStart(null);
          setDragEnd(null);
        }}
        onMouseLeave={() => {
          setDragStart(null);
          setDragEnd(null);
        }}
      >
        <Layer>
          {/* Track path */}
          <Path data={trackPath} stroke="var(--text-secondary)" strokeWidth={3} />

          {/* Committed window segments */}
          {committedSegments.map((seg, i) => (
            <Line
              key={`committed-${i}`}
              points={[seg.x1, seg.y1, seg.x2, seg.y2]}
              stroke="red"
              strokeWidth={3}
            />
          ))}

          {/* Preview window segments (while dragging) */}
          {previewSegments.map((seg, i) => (
            <Line
              key={`preview-${i}`}
              points={[seg.x1, seg.y1, seg.x2, seg.y2]}
              stroke="yellow"
              strokeWidth={2}
              opacity={0.7}
            />
          ))}

          {/* Car marker */}
          {carPos && <Circle x={carPos.x} y={carPos.y} radius={6} fill="white" />}
        </Layer>
      </Stage>

      {committedWindow && (
        <p style={{ margin: "0", fontSize: "12px", color: "var(--text-secondary)" }}>
          {formatTime(committedWindow[0])}–{formatTime(committedWindow[1])}
        </p>
      )}
    </div>
  );
}
