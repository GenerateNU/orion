// TrackVisualization.tsx
import React from "react";
import type { Segment } from "@features/dashboard/utils/trackmap";
import styles from "@features/dashboard/TrackMap.module.css";

export interface TrackVisualizationProps {
  // The whole track as a polyline `points` string, in SVG units.
  points: string;
  committedSegments: Segment[];
  previewSegments: Segment[];
  // The car marker. TrackMap moves it directly on hover, without re-rendering.
  carRef: React.RefObject<SVGCircleElement | null>;
  // The drawing's size in SVG units; also sets the element's aspect ratio.
  viewSize: { width: number; height: number };
  onMouseDown: (e: React.MouseEvent<SVGSVGElement>) => void;
  onMouseMove: (e: React.MouseEvent<SVGSVGElement>) => void;
  onMouseUp: (e: React.MouseEvent<SVGSVGElement>) => void;
  onMouseLeave: (e: React.MouseEvent<SVGSVGElement>) => void;
  stageRef: React.RefObject<SVGSVGElement | null>;
}

export const TrackVisualization = React.memo(function TrackVisualization({
  points,
  committedSegments,
  previewSegments,
  carRef,
  viewSize,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onMouseLeave,
  stageRef,
}: TrackVisualizationProps) {
  return (
    <svg
      ref={stageRef}
      viewBox={`0 0 ${viewSize.width} ${viewSize.height}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ aspectRatio: viewSize.width / viewSize.height }}
      className={styles.stage}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseLeave}
    >
      <polyline className={styles.track} points={points} />

      {committedSegments.map((seg, i) => (
        <line
          key={`committed-${i}`}
          className={styles.committed}
          x1={seg.x1}
          y1={seg.y1}
          x2={seg.x2}
          y2={seg.y2}
        />
      ))}

      {previewSegments.map((seg, i) => (
        <line
          key={`preview-${i}`}
          className={styles.preview}
          x1={seg.x1}
          y1={seg.y1}
          x2={seg.x2}
          y2={seg.y2}
        />
      ))}

      <circle ref={carRef} className={styles.car} r="2" visibility="hidden" />
    </svg>
  );
});
