/**
 * Helper functions for TrackMap component (SVG version)
 *
 * Every helper reads the cached position data (useRunPositions) in place: it
 * never maps, copies or mutates the arrays. Times here are the cached array's
 * own unit, epoch ms; TrackMap converts to and from RunTime at its edges.
 */

export type Position = [number, number]; // [x, y] in SVG units

// The cached data plus how to draw it: `project` turns one [lat, lon] into SVG
// coordinates, so no projected copy of the whole run is ever stored.
export interface Track {
  // [latitude, longitude], same length as `time`. The cached array: read only.
  latLon: readonly (readonly [number, number])[];
  // Epoch ms, ascending. The cached array: read only.
  time: Float64Array;
  project: (lat: number, lon: number) => Position;
  // The drawing's size in SVG units.
  viewSize: { width: number; height: number };
}

// Margin in SVG units so the stroke isn't clipped at the drawing's edges.
const PAD = 3;

/**
 * Fit the track into a drawing whose longer side is 100 SVG units, north up,
 * with the track's real proportions.
 */
export function makeTrack(
  latLon: readonly (readonly [number, number])[],
  time: Float64Array,
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
 * Convert mouse position to time (epoch ms) based on closest track point.
 *
 * Laps overlap, so several points can be under the mouse at once. With
 * `nearTime` (the drag's previous time, epoch ms), points far from it in time
 * are penalized, so a drag follows the lap it's on and only reaches the next
 * lap by going around.
 */
export function getTimeFromMouse(
  track: Track,
  mouseX: number,
  mouseY: number,
  nearTime?: number,
): number {
  const { time } = track;
  let bestScore = Infinity;
  let closestIdx = 0;
  let closestDist = 0;

  for (let i = 0; i < time.length; i++) {
    const [x, y] = pointAt(track, i);
    const dist = Math.hypot(mouseX - x, mouseY - y);
    const score =
      nearTime === undefined
        ? dist
        : dist + (Math.abs(time[i] - nearTime) / 1000) * TIME_PENALTY_PER_S;
    if (score < bestScore) {
      bestScore = score;
      closestIdx = i;
      closestDist = dist;
    }
  }

  // Interpolate time at closest index
  if (closestIdx === time.length - 1) {
    return time[closestIdx];
  }

  // Simple linear interpolation between closest points
  const t = Math.min(1, closestDist / 20); // Interpolate within 20px
  return time[closestIdx] + (time[closestIdx + 1] - time[closestIdx]) * t;
}

/**
 * Get car position (SVG units) at `atTime` (epoch ms) by interpolating x,y directly
 */
export function getCarPosition(
  track: Track,
  atTime: number | null,
): { x: number; y: number } | null {
  const { time } = track;
  if (atTime === null || time.length === 0) return null;

  // Find the two closest time points
  let idx = 0;
  for (let i = 0; i < time.length; i++) {
    if (time[i] <= atTime) idx = i;
    else break;
  }

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

export interface Segment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/**
 * Generate window line segments (committed or preview); start and end are epoch ms.
 */
export function generateSegments(track: Track, windowStart: number, windowEnd: number): Segment[] {
  const { time } = track;
  const segments: Segment[] = [];

  for (let i = 0; i < time.length - 1; i++) {
    // Check if this segment overlaps the window
    if (time[i + 1] >= windowStart && time[i] <= windowEnd) {
      const [x1, y1] = pointAt(track, i);
      const [x2, y2] = pointAt(track, i + 1);
      segments.push({ x1, y1, x2, y2 });
    }
  }

  return segments;
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
