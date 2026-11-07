import { memo } from "react";
import type { PointerEvent as ReactPointerEvent, RefObject } from "react";
import type { Point, Tick } from "@features/dashboard/utils/trackmap";
import { cx } from "@utils/classNames";
import styles from "./TrackMap.module.css";

export type DragMode = "car" | "edge";

type PointerHandler = (e: ReactPointerEvent<SVGSVGElement>) => void;

export interface TrackVisualizationProps {
  svgRef: RefObject<SVGSVGElement | null>;
  // The hover marker for other panels' hover time; TrackMap moves it directly.
  ghostRef: RefObject<SVGCircleElement | null>;
  // The drawing's size in SVG units; also sets the element's aspect ratio.
  viewSize: { width: number; height: number };
  // Path `d` strings, in SVG units: the whole run, its dropouts, the window.
  road: string;
  gaps: string;
  window: string;
  // A line across the track where the run starts.
  start: Tick;
  // The car, pointing in its direction of travel (degrees, SVG rotation).
  car: Point & { heading: number };
  // Lines across the track at the window's start and end; both are handles.
  edges: readonly [Tick, Tick];
  // The window is only a suggestion until it's committed: drawn fainter.
  pending: boolean;
  dragMode: DragMode | null;
  onPointerDown: PointerHandler;
  onPointerMove: PointerHandler;
  onPointerUp: PointerHandler;
  onPointerCancel: PointerHandler;
  onLostPointerCapture: PointerHandler;
}

// How far the "START" label sits past the outer end of its tick, in SVG units.
const LABEL_GAP = 3;

// An arrow pointing along +x (rotated to the heading), centred on the car's
// position, in SVG units.
const CAR_ARROW = "M2.6 0 L-1.9 2.1 L-0.9 0 L-1.9 -2.1 Z";

// A window edge: a bar across the track, like the ends of a range slider. Shaped
// differently from the car so it's clear which one moves and which one resizes.
function EdgeHandle({ tick, role }: { tick: Tick; role: "start" | "end" }) {
  const line = { x1: tick.x1, y1: tick.y1, x2: tick.x2, y2: tick.y2 };
  return (
    <g className={styles.handle} data-handle={role}>
      <title>Drag to resize the window</title>
      <line className={styles.handleOutline} {...line} />
      <line className={styles.handleBar} {...line} />
      <line className={styles.handleHit} {...line} />
    </g>
  );
}

export const TrackVisualization = memo(function TrackVisualization({
  svgRef,
  ghostRef,
  viewSize,
  road,
  gaps,
  window,
  start,
  car,
  edges,
  pending,
  dragMode,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onPointerCancel,
  onLostPointerCapture,
}: TrackVisualizationProps) {
  const labelBelow = start.outer.y > viewSize.height / 2;
  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${viewSize.width} ${viewSize.height}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ aspectRatio: viewSize.width / viewSize.height }}
      className={cx(styles.stage, dragMode && styles.dragging)}
      role="group"
      aria-label="Track map. Drag the car to move the selected window, or a handle to resize it."
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
      onLostPointerCapture={onLostPointerCapture}
    >
      <path className={styles.roadCasing} d={road} />
      <path className={styles.road} d={road} />
      <path className={styles.gap} d={gaps} />

      <g className={styles.start}>
        <line x1={start.x1} y1={start.y1} x2={start.x2} y2={start.y2} />
        <text
          x={start.outer.x}
          y={labelBelow ? start.outer.y + LABEL_GAP : start.outer.y - LABEL_GAP}
        >
          START
        </text>
      </g>

      <g className={cx(styles.window, pending && styles.pending)}>
        <path className={styles.windowGlow} d={window} />
        <path className={styles.windowLine} d={window} />
      </g>

      <EdgeHandle tick={edges[0]} role="start" />
      <EdgeHandle tick={edges[1]} role="end" />

      <circle ref={ghostRef} className={styles.ghost} r={1.3} visibility="hidden" />

      <g
        className={styles.car}
        data-handle="car"
        transform={`translate(${car.x} ${car.y}) rotate(${car.heading})`}
      >
        <title>Drag to move the window</title>
        <circle className={styles.carHalo} r={3.8} />
        <path className={styles.carBody} d={CAR_ARROW} />
        <circle className={styles.hitArea} r={4.5} />
      </g>
    </svg>
  );
});
