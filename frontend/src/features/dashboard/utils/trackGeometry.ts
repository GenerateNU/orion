import { clamp, type RunTime } from "@features/dashboard/utils/time";

// The run's path in local metres, for drawing and hit-testing the track map:
// x east and y north of the path's centre, on an equirectangular projection
// (well under a metre of error across a circuit). The arrays are parallel, one
// entry per estimated state, ascending in time.
export type TrackGeometry = {
  time: Float64Array; // RunTime
  x: Float64Array;
  y: Float64Array;
  bounds: Bounds;
};

export type Vec2 = { x: number; y: number };

export type Bounds = { minX: number; maxX: number; minY: number; maxY: number };

// A position on the path and the direction of travel there, in radians
// counter-clockwise from east.
export type TrackPoint = Vec2 & { heading: number };

const METRES_PER_DEGREE = (Math.PI / 180) * 6_371_008.8;

// null with fewer than two positions: there's no path to draw.
export function buildTrackGeometry(
  epochMs: Float64Array,
  positions: readonly (readonly [lat: number, lon: number])[],
  startMs: number,
): TrackGeometry | null {
  const n = Math.min(epochMs.length, positions.length);
  if (n < 2) return null;

  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLon = Infinity;
  let maxLon = -Infinity;
  for (let i = 0; i < n; i++) {
    const [lat, lon] = positions[i];
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
  }

  const lat0 = (minLat + maxLat) / 2;
  const lon0 = (minLon + maxLon) / 2;
  const metresPerLon = METRES_PER_DEGREE * Math.cos((lat0 * Math.PI) / 180);

  const time = new Float64Array(n);
  const x = new Float64Array(n);
  const y = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const [lat, lon] = positions[i];
    time[i] = epochMs[i] - startMs;
    x[i] = (lon - lon0) * metresPerLon;
    y[i] = (lat - lat0) * METRES_PER_DEGREE;
  }

  return {
    time,
    x,
    y,
    bounds: {
      minX: (minLon - lon0) * metresPerLon,
      maxX: (maxLon - lon0) * metresPerLon,
      minY: (minLat - lat0) * METRES_PER_DEGREE,
      maxY: (maxLat - lat0) * METRES_PER_DEGREE,
    },
  };
}

// The last sample at or before `t`, clamped to the path's ends.
export function indexAtTime(time: Float64Array, t: RunTime): number {
  let lo = 0;
  let hi = time.length - 1;
  if (t <= time[lo]) return lo;
  if (t >= time[hi]) return hi;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (time[mid] <= t) lo = mid;
    else hi = mid;
  }
  return lo;
}

// Interpolated between the samples either side of `t`.
export function positionAtTime(geometry: TrackGeometry, t: RunTime): Vec2 {
  const { time, x, y } = geometry;
  const i = indexAtTime(time, t);
  const j = Math.min(i + 1, time.length - 1);
  const span = time[j] - time[i];
  const f = span > 0 ? clamp((t - time[i]) / span, 0, 1) : 0;
  return { x: x[i] + (x[j] - x[i]) * f, y: y[i] + (y[j] - y[i]) * f };
}

// Heading is taken across ±HEADING_SPAN_MS rather than between neighbouring
// samples, which at 100 Hz are centimetres apart and noisy in direction.
const HEADING_SPAN_MS = 250;

export function pointAtTime(geometry: TrackGeometry, t: RunTime): TrackPoint {
  const behind = positionAtTime(geometry, t - HEADING_SPAN_MS);
  const ahead = positionAtTime(geometry, t + HEADING_SPAN_MS);
  return {
    ...positionAtTime(geometry, t),
    heading: Math.atan2(ahead.y - behind.y, ahead.x - behind.x),
  };
}

const distance2 = (geometry: TrackGeometry, i: number, target: Vec2) =>
  (geometry.x[i] - target.x) ** 2 + (geometry.y[i] - target.y) ** 2;

export type NearestOptions = {
  // Metres: samples further from the target don't count.
  reach: number;
  // Metres: passes this much further than the nearest one still count as ties.
  slack: number;
  // Ties go to the pass closest in time to this; null takes the nearest pass.
  preferTime: RunTime | null;
};

// The sample nearest `target`, or null when none is within reach. Each time the
// path comes within reach is one pass (a run of consecutive samples). Where laps
// overlap, several passes are about as near, and the one closest in time to
// `preferTime` wins, so a click stays on the lap being looked at.
export function nearestIndex(
  geometry: TrackGeometry,
  target: Vec2,
  { reach, slack, preferTime }: NearestOptions,
): number | null {
  const n = geometry.time.length;
  const reach2 = reach * reach;
  const passes: { index: number; distance: number }[] = [];
  let best = -1;
  let bestDistance2 = Infinity;
  for (let i = 0; i <= n; i++) {
    const d2 = i < n ? distance2(geometry, i, target) : Infinity;
    if (d2 <= reach2) {
      if (d2 < bestDistance2) {
        best = i;
        bestDistance2 = d2;
      }
    } else if (best !== -1) {
      passes.push({ index: best, distance: Math.sqrt(bestDistance2) });
      best = -1;
      bestDistance2 = Infinity;
    }
  }
  if (passes.length === 0) return null;

  const nearest = Math.min(...passes.map((pass) => pass.distance));
  const ties = passes.filter((pass) => pass.distance <= nearest + slack);
  const score = (pass: { index: number; distance: number }) =>
    preferTime === null ? pass.distance : Math.abs(geometry.time[pass.index] - preferTime);
  return ties.reduce((a, b) => (score(b) < score(a) ? b : a)).index;
}

// The sample nearest `target` within `span` ms either side of sample `from`. For
// dragging along the path: a handle follows its own lap instead of jumping to
// another pass nearby.
export function nearestIndexAround(
  geometry: TrackGeometry,
  target: Vec2,
  from: number,
  span: RunTime,
): number {
  const { time } = geometry;
  const lo = indexAtTime(time, time[from] - span);
  const hi = indexAtTime(time, time[from] + span);
  let best = from;
  let bestDistance2 = distance2(geometry, from, target);
  for (let i = lo; i <= hi; i++) {
    const d2 = distance2(geometry, i, target);
    if (d2 < bestDistance2) {
      best = i;
      bestDistance2 = d2;
    }
  }
  return best;
}
