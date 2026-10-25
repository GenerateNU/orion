import { useState, useMemo, useRef } from "react";
import { Stage, Layer, Path, Circle, Line } from "react-konva";
import {
  useCommittedWindow,
  useDashboardActions,
  useHoverTimeSubscription,
} from "../state/useDashboard";
import EmptyState from "../../../components/ui/EmptyState";

export function TrackMap() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const stageRef = useRef<any>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const { previewWindow, commitWindow } = useDashboardActions();
  const committedWindow = useCommittedWindow();

  // Mock data: 100 x,y points on oval, equally spaced over 120 seconds
  const mockRawPositions = useMemo(() => {
    return Array.from({ length: 100 }, (_, i) => {
      const angle = (i / 100) * 2 * Math.PI;
      const x = 150 + 150 * Math.cos(angle);
      const y = 100 + 100 * Math.sin(angle);
      return [x, y] as [number, number];
    });
  }, []);

  // Mock time scaled to match the URL run duration (~115 seconds in microseconds)
  // eslint-disable-next-line no-loss-of-precision
  const runDurationUs = 115642993357766642;
  const mockTime = useMemo(() => {
    return Array.from({ length: 100 }, (_, i) => (i / 100) * runDurationUs);
  }, []);

  // Convert x,y to track progress (0-100)
  const mockPositions = useMemo(() => {
    return mockRawPositions.map((_, i) => (i / 100) * 100);
  }, [mockRawPositions]);

  const positions = mockPositions;
  const time = mockTime;

  // Listen for hover time from other panels
  useHoverTimeSubscription((t) => {
    setHoverTime(t);
  });

  // Convert mouse position to time based on track angle
  const getTimeFromMouse = () => {
    if (!stageRef.current) return 0;
    const pointerPos = stageRef.current.getPointerPosition();
    if (!pointerPos) return 0;

    const dx = pointerPos.x - 150;
    const dy = pointerPos.y - 100;
    let angle = Math.atan2(dy, dx);

    // Normalize angle to 0-2π
    if (angle < 0) angle += 2 * Math.PI;

    // Convert angle to progress (0-100)
    const progress = (angle / (2 * Math.PI)) * 100;

    // Convert progress to time
    return (progress / 100) * time[time.length - 1];
  };

  // Get car position by interpolating between mock data points
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
      const pos = positions[idx];
      const angle = (pos / 100) * 2 * Math.PI;
      return {
        x: 150 + 150 * Math.cos(angle),
        y: 100 + 100 * Math.sin(angle),
      };
    }

    // Interpolate between idx and idx+1
    const t0 = time[idx];
    const t1 = time[idx + 1];
    const pos0 = positions[idx];
    const pos1 = positions[idx + 1];

    // Linear interpolation factor
    const factor = (hoverTimeVal - t0) / (t1 - t0);
    const interpolatedPos = pos0 + (pos1 - pos0) * factor;

    const angle = (interpolatedPos / 100) * 2 * Math.PI;
    return {
      x: 150 + 150 * Math.cos(angle),
      y: 100 + 100 * Math.sin(angle),
    };
  };

  // Generate oval track path
  const trackPath = useMemo(() => {
    const points: [number, number][] = [];
    for (let i = 0; i <= 360; i += 10) {
      const angle = (i * Math.PI) / 180;
      const x = 150 + 150 * Math.cos(angle);
      const y = 100 + 100 * Math.sin(angle);
      points.push([x, y]);
    }
    // Close the path
    points.push(points[0]);

    // Convert to path string
    let pathData = `M ${points[0][0]} ${points[0][1]}`;
    for (let i = 1; i < points.length; i++) {
      pathData += ` L ${points[i][0]} ${points[i][1]}`;
    }
    return pathData;
  }, []);

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

    console.log(
      "committedWindow segments: startIdx",
      startIdx,
      "endIdx",
      endIdx,
      "count:",
      endIdx - startIdx,
    );

    const segments: Array<{ x1: number; y1: number; x2: number; y2: number }> = [];

    for (let i = startIdx; i < endIdx && i < positions.length - 1; i++) {
      const pos1 = positions[i];
      const pos2 = positions[i + 1];
      const angle1 = (pos1 / 100) * 2 * Math.PI;
      const angle2 = (pos2 / 100) * 2 * Math.PI;
      const x1 = 150 + 150 * Math.cos(angle1);
      const y1 = 100 + 100 * Math.sin(angle1);
      const x2 = 150 + 150 * Math.cos(angle2);
      const y2 = 100 + 100 * Math.sin(angle2);

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
      const pos1 = positions[i];
      const pos2 = positions[i + 1];
      const angle1 = (pos1 / 100) * 2 * Math.PI;
      const angle2 = (pos2 / 100) * 2 * Math.PI;
      const x1 = 150 + 150 * Math.cos(angle1);
      const y1 = 100 + 100 * Math.sin(angle1);
      const x2 = 150 + 150 * Math.cos(angle2);
      const y2 = 100 + 100 * Math.sin(angle2);

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
      <div>
        <h3 style={{ margin: "0 0 4px 0", fontSize: "14px", fontWeight: "600" }}>Track position</h3>
        {committedWindow && (
          <p style={{ margin: "0", fontSize: "12px", color: "var(--text-secondary)" }}>
            Window {Math.round((committedWindow[0] / time[time.length - 1]) * 100)}% –{" "}
            {Math.round((committedWindow[1] / time[time.length - 1]) * 100)}%
          </p>
        )}
      </div>

      <Stage
        ref={stageRef}
        width={600}
        height={400}
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
          if (dragStart === null) return;
          const timeVal = getTimeFromMouse();
          setDragEnd(timeVal);
          const [start, end] = dragStart < timeVal ? [dragStart, timeVal] : [timeVal, dragStart];
          previewWindow([start, end]);
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

      <p style={{ margin: "0", fontSize: "12px", color: "var(--text-secondary)" }}>
        Window: whole run · Laps: none
      </p>
    </div>
  );
}
