// TrackVisualization.tsx
import React from "react";
import type { Segment } from "@features/dashboard/utils/trackmap";
import styles from "@features/dashboard/TrackMap.module.css";

export interface TrackVisualizationProps {
  svgPoints: Array<{ x: number; y: number }>;
  committedSegments: Segment[];
  previewSegments: Segment[];
  carPos: { x: number; y: number } | null;
  aspectRatio: number;
  onMouseDown: (e: React.MouseEvent<SVGSVGElement>) => void;
  onMouseMove: (e: React.MouseEvent<SVGSVGElement>) => void;
  onMouseUp: (e: React.MouseEvent<SVGSVGElement>) => void;
  onMouseLeave: (e: React.MouseEvent<SVGSVGElement>) => void;
  stageRef: React.RefObject<SVGSVGElement | null>;
}

export const TrackVisualization = React.memo(function TrackVisualization({
  svgPoints,
  committedSegments,
  previewSegments,
  carPos,
  aspectRatio,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onMouseLeave,
  stageRef,
}: TrackVisualizationProps) {
  return (
    <svg
      ref={stageRef}
      width="100%"
      height="auto"
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid meet"
      style={{ aspectRatio }}
      className={styles.stage}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseLeave}
    >
      <polyline
        points={svgPoints.map((p) => `${p.x},${p.y}`).join(" ")}
        stroke="#2563eb"
        strokeWidth="3"
        fill="none"
      />

      {committedSegments.map((seg, i) => (
        <line
          key={`committed-${i}`}
          x1={seg.x1}
          y1={seg.y1}
          x2={seg.x2}
          y2={seg.y2}
          stroke="#ef4444"
          strokeWidth="3"
        />
      ))}

      {previewSegments.map((seg, i) => (
        <line
          key={`preview-${i}`}
          x1={seg.x1}
          y1={seg.y1}
          x2={seg.x2}
          y2={seg.y2}
          stroke="#eab308"
          strokeWidth="2"
          opacity="0.7"
        />
      ))}

      {carPos && <circle cx={carPos.x} cy={carPos.y} r="2" fill="#ef4444" />}
    </svg>
  );
});
