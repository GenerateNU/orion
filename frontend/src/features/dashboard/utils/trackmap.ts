/**
 * Geometry for the track map (SVG).
 *
 * Every time a helper takes or returns is RunTime (ms since the run's start),
 * like the rest of the dashboard. The cached `time` array is epoch ms, so the
 * helpers convert with `track.startMs`, and nothing outside this file has to.
 *
 * Positions are projected once per track into two Float32Arrays (SVG units), so
 * hit-testing on every pointer move reads numbers instead of allocating tuples.
 * The cached `time` array is read in place, never copied or mutated.
 */

import type { RunTime } from "@features/dashboard/utils/time";

export type Point = { x: number; y: number };

export interface Track {
  // Epoch ms, ascending. The cached array: read only.
  time: Float64Array;
  // The run's start in epoch ms: RunTime = time[i] - startMs.
  startMs: number;
  // Projected positions in SVG units; NaN where the reading has no fix.
  xs: Float32Array;
  ys: Float32Array;
  // RunTime of the first and last samples with a position.
  firstTime: RunTime;
  lastTime: RunTime;
  // The drawing's size in SVG units (the longer side is 100).
  viewSize: { width: number; height: number };
}

// Samples further apart than this are a dropout: the line breaks there instead of
// cutting straight across the track, and nothing is interpolated across it.
export const GAP_MS = 2000;

// Margin in SVG units around the track: room for the handles and the start label.
const PAD = 8;

// A GPS reading of [0, 0] (or NaN) means no fix, not a car in the Gulf of Guinea.
const hasFix = (lat: number, lon: number) =>
  Number.isFinite(lat) && Number.isFinite(lon) && !(lat === 0 && lon === 0);

/**
 * Fit the track into a drawing whose longer side is 100 SVG units, north up,
 * with the track's real proportions. Null when no reading has a fix.
 */
export function makeTrack(
  latLon: readonly (readonly [number, number])[],
  time: Float64Array,
  startMs: number,
): Track | null {
  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLon = Infinity;
  let maxLon = -Infinity;
  let first = -1;
  let last = -1;
  // A loop, not Math.min(...array): spreading a whole run (100 Hz) overflows the stack.
  for (let i = 0; i < latLon.length; i++) {
    const [lat, lon] = latLon[i];
    if (!hasFix(lat, lon)) continue;
    if (first < 0) first = i;
    last = i;
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLon = Math.min(minLon, lon);
    maxLon = Math.max(maxLon, lon);
  }
  if (first < 0) return null;

  // A degree of longitude is shorter than a degree of latitude away from the
  // equator, so scale it by cos(latitude) to keep the track's real proportions.
  const lonScale = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
  const width = (maxLon - minLon) * lonScale || 1e-9;
  const height = maxLat - minLat || 1e-9;
  // One scale for both axes, so the shape isn't stretched.
  const scale = (100 - 2 * PAD) / Math.max(width, height);

  const xs = new Float32Array(latLon.length);
  const ys = new Float32Array(latLon.length);
  for (let i = 0; i < latLon.length; i++) {
    const [lat, lon] = latLon[i];
    if (hasFix(lat, lon)) {
      xs[i] = PAD + (lon - minLon) * lonScale * scale;
      // SVG y grows downward: subtract from maxLat so north is up.
      ys[i] = PAD + (maxLat - lat) * scale;
    } else {
      xs[i] = NaN;
      ys[i] = NaN;
    }
  }

  return {
    time,
    startMs,
    xs,
    ys,
    firstTime: time[first] - startMs,
    lastTime: time[last] - startMs,
    viewSize: { width: width * scale + 2 * PAD, height: height * scale + 2 * PAD },
  };
}

const valid = (track: Track, i: number) => !Number.isNaN(track.xs[i]);
const fmt = (n: number) => n.toFixed(2);

// Index of the last sample at or before `at` (epoch ms), by binary search; 0 if none.
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
 * An SVG path `d` through (t, x, y) entries in time order. The pen lifts at
 * readings without a fix and across dropouts, so gaps aren't drawn as chords.
 */
function pathThrough(entries: Iterable<readonly [number, number, number]>): string {
  let d = "";
  let prevT = NaN;
  for (const [t, x, y] of entries) {
    if (Number.isNaN(x)) {
      prevT = NaN;
      continue;
    }
    d += `${Number.isNaN(prevT) || t - prevT > GAP_MS ? "M" : "L"}${fmt(x)} ${fmt(y)}`;
    prevT = t;
  }
  return d;
}

function* samples(track: Track, from: number, to: number) {
  for (let i = from; i <= to; i++) yield [track.time[i], track.xs[i], track.ys[i]] as const;
}

/** The whole run's path, broken at dropouts. */
export function trackPath(track: Track): string {
  return pathThrough(samples(track, 0, track.time.length - 1));
}

/** Short straight segments across each dropout, drawn faintly so gaps read as gaps. */
export function gapPath(track: Track): string {
  const { time, xs, ys } = track;
  let d = "";
  for (let i = 1; i < time.length; i++) {
    if (time[i] - time[i - 1] > GAP_MS && valid(track, i) && valid(track, i - 1)) {
      d += `M${fmt(xs[i - 1])} ${fmt(ys[i - 1])}L${fmt(xs[i])} ${fmt(ys[i])}`;
    }
  }
  return d;
}

/**
 * Where the car was at `runTime`, interpolated between samples. Null outside the
 * recorded range, inside a dropout, or next to a reading without a fix.
 */
export function positionAt(track: Track, runTime: RunTime | null): Point | null {
  const { time, xs, ys } = track;
  if (runTime === null || time.length === 0) return null;
  const at = runTime + track.startMs;
  if (at < time[0] || at > time[time.length - 1]) return null;
  const i = indexAt(time, at);
  if (!valid(track, i)) return null;
  if (at === time[i] || i === time.length - 1) return { x: xs[i], y: ys[i] };
  const j = i + 1;
  if (!valid(track, j) || time[j] - time[i] > GAP_MS) return null;
  const f = (at - time[i]) / (time[j] - time[i]);
  return { x: xs[i] + (xs[j] - xs[i]) * f, y: ys[i] + (ys[j] - ys[i]) * f };
}

/**
 * The part of the run between `from` and `to` (RunTime) as a path `d`, starting
 * and ending exactly at those times so the handles sit on its ends.
 */
export function windowPath(track: Track, from: RunTime, to: RunTime): string {
  const { time, startMs } = track;
  if (time.length === 0 || to <= from) return "";
  const a = positionAt(track, from);
  const b = positionAt(track, to);
  const fromMs = from + startMs;
  const toMs = to + startMs;
  // First sample after `from`, last at or before `to`.
  const i0 = time[0] > fromMs ? 0 : indexAt(time, fromMs) + 1;
  const i1 = indexAt(time, toMs);
  function* entries() {
    if (a) yield [fromMs, a.x, a.y] as const;
    if (time[i1] <= toMs) yield* samples(track, i0, i1);
    if (b) yield [toMs, b.x, b.y] as const;
  }
  return pathThrough(entries());
}

/**
 * Where to draw a marker for `runTime`: on the path when possible, else at the
 * nearest recorded sample (before the first fix, after the last, or in a gap).
 */
export function anchorAt(track: Track, runTime: RunTime): Point & { index: number } {
  const clamped = Math.min(Math.max(runTime, track.firstTime), track.lastTime);
  let index = indexAt(track.time, clamped + track.startMs);
  while (index > 0 && !valid(track, index)) index--;
  while (index < track.time.length - 1 && !valid(track, index)) index++;
  const exact = positionAt(track, clamped);
  return { ...(exact ?? { x: track.xs[index], y: track.ys[index] }), index };
}

// Unit vector along the direction of travel at sample `i`. Looks past repeated
// readings (a stationary or slow GPS repeats positions) and never across a gap.
function directionAt(track: Track, i: number): Point {
  const { time, xs, ys } = track;
  const MIN_STEP = 0.3; // SVG units
  const reach = (step: 1 | -1) => {
    let k = i;
    for (let n = 0; n < 200; n++) {
      const next = k + step;
      if (next < 0 || next >= time.length || !valid(track, next)) break;
      if (Math.abs(time[next] - time[k]) > GAP_MS) break;
      k = next;
      if (Math.hypot(xs[k] - xs[i], ys[k] - ys[i]) >= MIN_STEP) break;
    }
    return k;
  };
  const a = reach(-1);
  const b = reach(1);
  const dx = xs[b] - xs[a];
  const dy = ys[b] - ys[a];
  const len = Math.hypot(dx, dy);
  return len > 0 ? { x: dx / len, y: dy / len } : { x: 1, y: 0 };
}

/** The direction of travel at a marker, in degrees (0 = east, clockwise in SVG). */
export function headingAt(track: Track, at: { index: number }): number {
  const dir = directionAt(track, at.index);
  return (Math.atan2(dir.y, dir.x) * 180) / Math.PI;
}

export interface Tick {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  // The end on the outside of the track (away from the drawing's centre).
  outer: Point;
}

/** A short line across the track at `at`, `halfLength` SVG units each side. */
export function tickAt(track: Track, at: Point & { index: number }, halfLength: number): Tick {
  const dir = directionAt(track, at.index);
  const nx = -dir.y * halfLength;
  const ny = dir.x * halfLength;
  const p1 = { x: at.x + nx, y: at.y + ny };
  const p2 = { x: at.x - nx, y: at.y - ny };
  const cx = track.viewSize.width / 2;
  const cy = track.viewSize.height / 2;
  const outer = Math.hypot(p1.x - cx, p1.y - cy) > Math.hypot(p2.x - cx, p2.y - cy) ? p1 : p2;
  return { x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y, outer };
}

// While dragging, moving 1 s along the run costs as much as being this many SVG
// units further from the pointer (the drawing's longer side is 100). Big enough
// that jumping to another lap (tens of seconds) never beats following the current
// one; small enough that following the pointer along the lap always wins.
const TIME_PENALTY_PER_S = 0.1;

/**
 * The recorded sample nearest the point (x, y), as a RunTime, and its plain
 * distance in SVG units. Laps overlap, so with `nearTime` samples far from it in
 * time are penalized: a drag follows the lap it's on. Null if nothing has a fix.
 */
export function nearestSample(
  track: Track,
  x: number,
  y: number,
  nearTime?: RunTime,
): { time: RunTime; dist: number } | null {
  const { time, xs, ys, startMs } = track;
  const near = nearTime === undefined ? undefined : nearTime + startMs;
  let best = -1;
  let bestScore = Infinity;
  let bestDist = Infinity;
  for (let i = 0; i < time.length; i++) {
    const px = xs[i];
    if (Number.isNaN(px)) continue;
    const dist = Math.hypot(x - px, y - ys[i]);
    const score =
      near === undefined ? dist : dist + (Math.abs(time[i] - near) / 1000) * TIME_PENALTY_PER_S;
    if (score < bestScore) {
      bestScore = score;
      best = i;
      bestDist = dist;
    }
  }
  return best < 0 ? null : { time: time[best] - startMs, dist: bestDist };
}
