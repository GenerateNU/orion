import {
  indexAtTime,
  pointAtTime,
  positionAtTime,
  type TrackGeometry,
  type TrackPoint,
} from "@features/dashboard/utils/trackGeometry";
import type { TrackHandle, TrackSelection } from "@features/dashboard/utils/trackSelection";
import type { RunTime } from "@features/dashboard/utils/time";
import { toScreen, type Size, type ViewTransform } from "@features/dashboard/utils/trackView";

// How the track map looks: canvas drawing for each of its layers. Plain functions
// of what to draw, with no state and no input handling.

// Colours come from CSS custom properties on the map (TrackMap.module.css), so
// they follow the app's light and dark tokens.
export type TrackMapTheme = {
  track: string;
  window: string;
  notch: string;
  point: string;
  halo: string;
  hover: string;
};

const THEME_PROPERTIES: Record<keyof TrackMapTheme, string> = {
  track: "--track-line",
  window: "--track-window",
  notch: "--track-notch",
  point: "--track-point",
  halo: "--track-halo",
  hover: "--track-hover",
};

export function readTrackMapTheme(element: Element): TrackMapTheme {
  const style = getComputedStyle(element);
  const read = (key: keyof TrackMapTheme) => style.getPropertyValue(THEME_PROPERTIES[key]).trim();
  return {
    track: read("track"),
    window: read("window"),
    notch: read("notch"),
    point: read("point"),
    halo: read("halo"),
    hover: read("hover"),
  };
}

// CSS pixels.
const TRACK_WIDTH = 3;
const WINDOW_WIDTH = 6;
const HALO_WIDTH = 3;
const NOTCH_LENGTH = 22;
const NOTCH_WIDTH = 4;
const NOTCH_EMPHASIS_WIDTH = 6;
const POINT_RADIUS = 7;
const POINT_EMPHASIS_RADIUS = 9;
const HOVER_RADIUS = 5;
// The rest of the track fades behind a selected window.
const DIMMED_ALPHA = 0.35;
// Samples closer than this to the last one drawn are skipped: at 100 Hz most of
// them land on the same pixel.
const MIN_SEGMENT_PX = 0.75;

// Sizes the canvas's backing store for the display's pixel ratio (only when it
// changes, which would clear it anyway), clears it, and returns a context drawing
// in CSS pixels.
export function prepareCanvas(
  canvas: HTMLCanvasElement | null,
  size: Size,
): CanvasRenderingContext2D | null {
  const context = canvas?.getContext("2d");
  if (!canvas || !context) return null;
  const ratio = window.devicePixelRatio || 1;
  const width = Math.round(size.width * ratio);
  const height = Math.round(size.height * ratio);
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, size.width, size.height);
  return context;
}

// Adds the path between two run times to the context's current path, starting and
// ending at the interpolated positions so a window's ends meet its notches.
function traceSpan(
  context: CanvasRenderingContext2D,
  geometry: TrackGeometry,
  view: ViewTransform,
  from: RunTime,
  to: RunTime,
) {
  const first = toScreen(view, positionAtTime(geometry, from));
  context.moveTo(first.x, first.y);
  let last = first;
  const end = indexAtTime(geometry.time, to);
  for (let i = indexAtTime(geometry.time, from) + 1; i <= end; i++) {
    const at = toScreen(view, { x: geometry.x[i], y: geometry.y[i] });
    if (Math.abs(at.x - last.x) + Math.abs(at.y - last.y) < MIN_SEGMENT_PX) continue;
    context.lineTo(at.x, at.y);
    last = at;
  }
  const final = toScreen(view, positionAtTime(geometry, to));
  context.lineTo(final.x, final.y);
}

function strokeRound(context: CanvasRenderingContext2D, colour: string, width: number) {
  context.strokeStyle = colour;
  context.lineWidth = width;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.stroke();
}

// The whole run's path: the base layer, redrawn only when the track or its size changes.
export function drawTrack(
  context: CanvasRenderingContext2D,
  geometry: TrackGeometry,
  view: ViewTransform,
  theme: TrackMapTheme,
  dimmed: boolean,
) {
  const { time } = geometry;
  context.globalAlpha = dimmed ? DIMMED_ALPHA : 1;
  context.beginPath();
  traceSpan(context, geometry, view, time[0], time[time.length - 1]);
  strokeRound(context, theme.track, TRACK_WIDTH);
  context.globalAlpha = 1;
}

// A tick across the track at a window bound, square to the direction of travel.
function drawNotch(
  context: CanvasRenderingContext2D,
  view: ViewTransform,
  at: TrackPoint,
  theme: TrackMapTheme,
  emphasis: boolean,
) {
  const centre = toScreen(view, at);
  // Screen y points down, so the track's normal (−sin, cos) becomes (sin, cos).
  const dx = (Math.sin(at.heading) * NOTCH_LENGTH) / 2;
  const dy = (Math.cos(at.heading) * NOTCH_LENGTH) / 2;
  const width = emphasis ? NOTCH_EMPHASIS_WIDTH : NOTCH_WIDTH;
  context.beginPath();
  context.moveTo(centre.x - dx, centre.y - dy);
  context.lineTo(centre.x + dx, centre.y + dy);
  strokeRound(context, theme.halo, width + 2 * HALO_WIDTH);
  strokeRound(context, theme.notch, width);
}

// The selected point: a dot with an arrowhead pointing the way the car is going.
function drawPointMarker(
  context: CanvasRenderingContext2D,
  view: ViewTransform,
  at: TrackPoint,
  theme: TrackMapTheme,
  emphasis: boolean,
) {
  const centre = toScreen(view, at);
  const radius = emphasis ? POINT_EMPHASIS_RADIUS : POINT_RADIUS;
  context.save();
  context.translate(centre.x, centre.y);
  context.rotate(-at.heading);
  context.beginPath();
  context.arc(0, 0, radius, 0, 2 * Math.PI);
  context.moveTo(radius + 9, 0);
  context.lineTo(radius - 2, -radius * 0.9);
  context.lineTo(radius - 2, radius * 0.9);
  context.closePath();
  context.lineJoin = "round";
  context.strokeStyle = theme.halo;
  context.lineWidth = HALO_WIDTH;
  context.stroke();
  context.fillStyle = theme.point;
  context.fill();
  context.restore();
}

// The selection layer: the window's stretch of track, its notches and the point.
// `emphasis` enlarges the handle being hovered or dragged.
export function drawSelection(
  context: CanvasRenderingContext2D,
  geometry: TrackGeometry,
  view: ViewTransform,
  theme: TrackMapTheme,
  selection: TrackSelection,
  emphasis: TrackHandle | null,
) {
  const [from, to] = selection.window;
  context.beginPath();
  traceSpan(context, geometry, view, from, to);
  strokeRound(context, theme.window, WINDOW_WIDTH);

  drawNotch(context, view, pointAtTime(geometry, from), theme, emphasis === "start");
  drawNotch(context, view, pointAtTime(geometry, to), theme, emphasis === "end");
  drawPointMarker(
    context,
    view,
    pointAtTime(geometry, selection.point),
    theme,
    emphasis === "point",
  );
}

// The hover layer: where the time under the pointer (on any panel) is on track.
export function drawHover(
  context: CanvasRenderingContext2D,
  geometry: TrackGeometry,
  view: ViewTransform,
  theme: TrackMapTheme,
  time: RunTime,
) {
  const centre = toScreen(view, positionAtTime(geometry, time));
  context.beginPath();
  context.arc(centre.x, centre.y, HOVER_RADIUS, 0, 2 * Math.PI);
  context.fillStyle = theme.halo;
  context.fill();
  context.strokeStyle = theme.hover;
  context.lineWidth = 2.5;
  context.stroke();
}
