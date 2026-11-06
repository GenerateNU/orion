/**
 * Helper functions for TrackMap component (SVG version)
 *
 * Every helper reads the cached position data (useRunPositions) in place: it
 * never maps, copies or mutates the arrays.
 *
 * Every time a helper takes or returns is RunTime (ms since the run's start),
 * like the rest of the dashboard. The cached `time` array is epoch ms, so the
 * helpers convert with `track.startMs`, and nothing outside this file has to.
 */

import type { RunTime } from "@features/dashboard/utils/time";

export type Position = [number, number]; // [x, y] in SVG units

// The cached data plus how to draw it: `project` turns one [lat, lon] into SVG
// coordinates, so no projected copy of the whole run is ever stored.
export interface Track {
  // [latitude, longitude], same length as `time`. The cached array: read only.
  latLon: readonly (readonly [number, number])[];
  // Epoch ms, ascending. The cached array: read only.
  time: Float64Array;
  // The run's start in epoch ms: RunTime = time[i] - startMs.
  startMs: number;
  project: (lat: number, lon: number) => Position;
  // The drawing's size in SVG units.
  viewSize: { width: number; height: number };
}

// Margin in SVG units around the track: room for the lines across it and the
// "S/F" label, so nothing is clipped at the drawing's edges.
const PAD = 8;

/**
 * Fit the track into a drawing whose longer side is 100 SVG units, north up,
 * with the track's real proportions.
 */
export function makeTrack(
  latLon: readonly (readonly [number, number])[],
  time: Float64Array,
  startMs: number,
): Track {
  // A loop, not Math.min(...array): spreading a whole run (100 Hz) overflows the stack.
  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLon = Infinity;
  let maxLon = -Infinity;
  for (const [lat, lon] of latLon) {
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
  }

  // A degree of longitude is shorter than a degree of latitude away from the
  // equator, so scale it by cos(latitude) to keep the track's real proportions.
  const lonScale = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
  const width = (maxLon - minLon) * lonScale || 1;
  const height = maxLat - minLat || 1;

  // One scale for both axes, so the shape isn't stretched.
  const scale = (100 - 2 * PAD) / Math.max(width, height);
  const project = (lat: number, lon: number): Position => [
    PAD + (lon - minLon) * lonScale * scale,
    // SVG y grows downward: subtract from maxLat so north is up.
    PAD + (maxLat - lat) * scale,
  ];

  return {
    latLon,
    time,
    startMs,
    project,
    viewSize: { width: width * scale + 2 * PAD, height: height * scale + 2 * PAD },
  };
}

/** The whole track as an SVG polyline `points` string. */
export function trackPoints(track: Track): string {
  let points = "";
  for (const [lat, lon] of track.latLon) {
    const [x, y] = track.project(lat, lon);
    points += `${x},${y} `;
  }
  return points;
}

const pointAt = (track: Track, i: number): Position =>
  track.project(track.latLon[i][0], track.latLon[i][1]);

// While dragging, moving 1 s along the run costs as much as being this many SVG
// units further from the mouse (the drawing's longer side is 100). Big enough
// that jumping a lap (tens of seconds) never beats following the current one;
// small enough that following the mouse along the lap always wins.
const TIME_PENALTY_PER_S = 0.1;

/**
 * Convert mouse position to a RunTime based on closest track point.
 *
 * Laps overlap, so several points can be under the mouse at once. With
 * `nearTime` (the drag's previous time), points far from it in time are
 * penalized, so a drag follows the lap it's on and only reaches the next
 * lap by going around.
 */
export function getTimeFromMouse(
  track: Track,
  mouseX: number,
  mouseY: number,
  nearTime?: RunTime,
): RunTime {
  const { time, startMs } = track;
  const near = nearTime === undefined ? undefined : nearTime + startMs;
  let bestScore = Infinity;
  let closestIdx = 0;
  let closestDist = 0;

  for (let i = 0; i < time.length; i++) {
    const [x, y] = pointAt(track, i);
    const dist = Math.hypot(mouseX - x, mouseY - y);
    const score =
      near === undefined ? dist : dist + (Math.abs(time[i] - near) / 1000) * TIME_PENALTY_PER_S;
    if (score < bestScore) {
      bestScore = score;
      closestIdx = i;
      closestDist = dist;
    }
  }

  // Interpolate time at closest index
  if (closestIdx === time.length - 1) {
    return time[closestIdx] - startMs;
  }

  // Simple linear interpolation between closest points
  const t = Math.min(1, closestDist / 20); // Interpolate within 20px
  return time[closestIdx] + (time[closestIdx + 1] - time[closestIdx]) * t - startMs;
}

/**
 * Get car position (SVG units) at `runTime` by interpolating x,y directly
 */
export function getCarPosition(
  track: Track,
  runTime: RunTime | null,
): { x: number; y: number } | null {
  const { time } = track;
  if (runTime === null || time.length === 0) return null;
  const atTime = runTime + track.startMs;

  // The sample at or before `atTime`; the car is between it and the next one.
  const idx = indexAt(time, atTime);

  const [x0, y0] = pointAt(track, idx);
  if (idx === time.length - 1) {
    // At or past the end
    return { x: x0, y: y0 };
  }

  // Interpolate between idx and idx+1
  const t0 = time[idx];
  const t1 = time[idx + 1];

  // Divide-by-zero guard
  if (t1 === t0) {
    return { x: x0, y: y0 };
  }

  // Linear interpolation factor
  const [x1, y1] = pointAt(track, idx + 1);
  const factor = (atTime - t0) / (t1 - t0);
  return { x: x0 + (x1 - x0) * factor, y: y0 + (y1 - y0) * factor };
}

// Index of the last sample at or before `at` (epoch ms), by binary search.
function indexAt(time: Float64Array, at: number): number {
  let lo = 0;
  let hi = time.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (time[mid] <= at) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

/**
 * The part of the track between `windowStart` and `windowEnd` (RunTime), as an
 * SVG polyline `points` string. One element however long the window is.
 */
export function windowPoints(track: Track, windowStart: RunTime, windowEnd: RunTime): string {
  const { time, startMs } = track;
  if (time.length === 0) return "";
  // Include the samples either side of the window, so the line reaches its edges.
  const first = indexAt(time, windowStart + startMs);
  const last = Math.min(time.length - 1, indexAt(time, windowEnd + startMs) + 1);
  let points = "";
  for (let i = first; i <= last; i++) {
    const [x, y] = pointAt(track, i);
    points += `${x},${y} `;
  }
  return points;
}

export interface Tick {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  // The end on the outside of the track (away from the drawing's centre).
  outer: { x: number; y: number };
}

/**
 * A short line across the track at `runTime`, `halfLength` SVG units each side:
 * for the window's edges.
 */
export function tickAt(track: Track, runTime: RunTime, halfLength: number): Tick | null {
  return tickAtIndex(track, indexAt(track.time, runTime + track.startMs), halfLength);
}

/** The start/finish line: a tick at the run's first sample, where it starts. */
export function startFinishTick(track: Track, halfLength: number): Tick | null {
  return tickAtIndex(track, 0, halfLength);
}

function tickAtIndex(track: Track, i: number, halfLength: number): Tick | null {
  const { time, viewSize } = track;
  if (time.length < 2) return null;
  const [x, y] = pointAt(track, i);
  // Direction of travel from the neighbouring samples; the tick is perpendicular.
  const [ax, ay] = pointAt(track, Math.max(0, i - 1));
  const [bx, by] = pointAt(track, Math.min(time.length - 1, i + 1));
  const len = Math.hypot(bx - ax, by - ay) || 1;
  const nx = (-(by - ay) / len) * halfLength;
  const ny = ((bx - ax) / len) * halfLength;
  const p1 = { x: x + nx, y: y + ny };
  const p2 = { x: x - nx, y: y - ny };
  const cx = viewSize.width / 2;
  const cy = viewSize.height / 2;
  const outer = Math.hypot(p1.x - cx, p1.y - cy) > Math.hypot(p2.x - cx, p2.y - cy) ? p1 : p2;
  return { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, outer };
}

export function getMousePosOnSVG(
  event: React.MouseEvent<SVGSVGElement>,
  stageRef: React.RefObject<SVGSVGElement | null>,
): { x: number; y: number } | null {
  // Track points are in viewBox units, not screen pixels: map the mouse through
  // the SVG's screen transform so hit-testing works at any rendered size.
  const svg = stageRef.current;
  const ctm = svg?.getScreenCTM();
  if (!svg || !ctm) return null;
  const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(ctm.inverse());
  return { x: point.x, y: point.y };
}
