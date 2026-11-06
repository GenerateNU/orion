// TrackVisualization.tsx
import React from "react";
import type { Tick } from "@features/dashboard/utils/trackmap";
import styles from "@features/dashboard/TrackMap.module.css";

export interface TrackVisualizationProps {
  // The whole track as a polyline `points` string, in SVG units.
  points: string;
  // The committed window and the window being dragged, as `points` strings
  // ("" when there is none).
  committedPoints: string;
  previewPoints: string;
  // Lines across the track at the shown window's edges, and at start/finish.
  windowTicks: Tick[];
  startFinish: Tick | null;
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

// How far the "S/F" label sits past the outer end of its tick, in SVG units.
const LABEL_GAP = 3.5;

export const TrackVisualization = React.memo(function TrackVisualization({
  points,
  committedPoints,
  previewPoints,
  windowTicks,
  startFinish,
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

      {committedPoints && <polyline className={styles.committed} points={committedPoints} />}
      {previewPoints && <polyline className={styles.preview} points={previewPoints} />}

      {windowTicks.map((tick, i) => (
        <line
          key={i}
          className={styles.windowTick}
          x1={tick.x1}
          y1={tick.y1}
          x2={tick.x2}
          y2={tick.y2}
        />
      ))}

      {startFinish && (
        <g className={styles.startFinish}>
          <line x1={startFinish.x1} y1={startFinish.y1} x2={startFinish.x2} y2={startFinish.y2} />
          {/* Below the tick in the bottom half of the drawing, above it in the top. */}
          <text
            x={startFinish.outer.x}
            y={
              startFinish.outer.y > viewSize.height / 2
                ? startFinish.outer.y + LABEL_GAP
                : startFinish.outer.y - LABEL_GAP
            }
          >
            S/F
          </text>
        </g>
      )}

      <circle ref={carRef} className={styles.car} r="1.8" visibility="hidden" />
    </svg>
  );
});
