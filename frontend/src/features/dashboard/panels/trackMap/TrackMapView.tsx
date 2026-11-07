import { useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import type { DOMAttributes, Ref, RefObject } from "react";
import type { TrackGeometry } from "@features/dashboard/utils/trackGeometry";
import type { TrackHandle, TrackSelection } from "@features/dashboard/utils/trackSelection";
import type { RunTime } from "@features/dashboard/utils/time";
import { cx } from "@utils/classNames";
import type { Size, ViewTransform } from "@features/dashboard/utils/trackView";
import {
  drawHover,
  drawSelection,
  drawTrack,
  prepareCanvas,
  readTrackMapTheme,
  type TrackMapTheme,
} from "./trackDrawing";
import styles from "./TrackMap.module.css";

// The track map's presentation: three stacked canvases, each redrawn only when
// what it shows changes.
//   base       the whole path               (track, size, theme)
//   selection  window, notches and point    (each preview frame of a drag)
//   hover      the hover marker             (imperatively, through `handleRef`)
// Hover moves up to once a frame from any panel, so it skips React rendering.

export type TrackMapViewHandle = {
  showHover: (time: RunTime | null) => void;
};

type StageEvents = Pick<
  DOMAttributes<HTMLDivElement>,
  | "onPointerDown"
  | "onPointerMove"
  | "onPointerUp"
  | "onPointerCancel"
  | "onPointerLeave"
  | "onKeyDown"
>;

type TrackMapViewProps = {
  // Measured by the caller, which fits `transform` to it.
  stageRef: Ref<HTMLDivElement>;
  handleRef: Ref<TrackMapViewHandle>;
  geometry: TrackGeometry;
  size: Size | null;
  transform: ViewTransform | null;
  durationMs: number;
  selection: TrackSelection | null;
  activeHandle: TrackHandle | null;
  hoveredHandle: TrackHandle | null;
  events: StageEvents;
};

const formatSeconds = (ms: number) => `${(ms / 1000).toFixed(1)} s`;

// Re-read when the colour scheme flips, since the tokens behind it change.
function useTrackMapTheme(ref: RefObject<HTMLElement | null>): TrackMapTheme | null {
  const [theme, setTheme] = useState<TrackMapTheme | null>(null);
  useEffect(() => {
    const read = () => {
      if (ref.current) setTheme(readTrackMapTheme(ref.current));
    };
    read();
    const scheme = window.matchMedia("(prefers-color-scheme: dark)");
    scheme.addEventListener("change", read);
    return () => scheme.removeEventListener("change", read);
  }, [ref]);
  return theme;
}

export function TrackMapView({
  stageRef,
  handleRef,
  geometry,
  size,
  transform,
  durationMs,
  selection,
  activeHandle,
  hoveredHandle,
  events,
}: TrackMapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const baseRef = useRef<HTMLCanvasElement>(null);
  const selectionRef = useRef<HTMLCanvasElement>(null);
  const hoverRef = useRef<HTMLCanvasElement>(null);
  const theme = useTrackMapTheme(mapRef);

  const dimmed = selection !== null;
  useEffect(() => {
    if (!size || !transform || !theme) return;
    const context = prepareCanvas(baseRef.current, size);
    if (context) drawTrack(context, geometry, transform, theme, dimmed);
  }, [geometry, size, transform, theme, dimmed]);

  const emphasis = activeHandle ?? hoveredHandle;
  useEffect(() => {
    if (!size || !transform || !theme) return;
    const context = prepareCanvas(selectionRef.current, size);
    if (context && selection) {
      drawSelection(context, geometry, transform, theme, selection, emphasis);
    }
  }, [geometry, size, transform, theme, selection, emphasis]);

  // The hover layer draws from refs, at most once a frame.
  const scene = useRef({ geometry, size, transform, theme });
  const hoverTime = useRef<RunTime | null>(null);
  const hoverFrame = useRef(0);

  const paintHover = useCallback(() => {
    hoverFrame.current = 0;
    const { geometry, size, transform, theme } = scene.current;
    if (!size || !transform || !theme) return;
    const context = prepareCanvas(hoverRef.current, size);
    if (context && hoverTime.current !== null) {
      drawHover(context, geometry, transform, theme, hoverTime.current);
    }
  }, []);

  useEffect(() => {
    scene.current = { geometry, size, transform, theme };
    paintHover();
  }, [geometry, size, transform, theme, paintHover]);
  useEffect(() => () => cancelAnimationFrame(hoverFrame.current), []);

  useImperativeHandle(
    handleRef,
    () => ({
      showHover: (time) => {
        hoverTime.current = time;
        if (!hoverFrame.current) hoverFrame.current = requestAnimationFrame(paintHover);
      },
    }),
    [paintHover],
  );

  return (
    <div ref={mapRef} className={styles.map}>
      <div
        ref={stageRef}
        className={cx(styles.stage, activeHandle ? styles.grabbing : hoveredHandle && styles.grab)}
        tabIndex={0}
        role="slider"
        aria-label="Selected point on track"
        aria-valuemin={0}
        aria-valuemax={durationMs / 1000}
        aria-valuenow={selection ? selection.point / 1000 : 0}
        aria-valuetext={
          selection
            ? `${formatSeconds(selection.point)}, window ${formatSeconds(selection.window[0])} to ${formatSeconds(selection.window[1])}`
            : "No point selected"
        }
        {...events}
      >
        <canvas ref={baseRef} className={styles.layer} />
        <canvas ref={selectionRef} className={styles.layer} />
        <canvas ref={hoverRef} className={styles.layer} />
      </div>
      <p className={styles.hint}>
        Click the track to place the point. Drag the point or a notch; ← → to step.
      </p>
    </div>
  );
}
