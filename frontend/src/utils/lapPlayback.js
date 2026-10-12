// Helpers for replaying a lap: when each point happened, where the car is at any
// moment in between, and how fast it was going there.

// Seconds since the lap's first point, one per position. Falls back to 0.1s
// apart when timestamps are missing or unreadable, and never goes backwards.
export function lapTimes(positions) {
  const t0 = Date.parse(positions[0]?.timestamp);
  const times = positions.map((p, i) => {
    const t = Date.parse(p.timestamp);
    return Number.isFinite(t) && Number.isFinite(t0) ? (t - t0) / 1000 : i * 0.1;
  });
  for (let i = 1; i < times.length; i++) {
    times[i] = Math.max(times[i], times[i - 1]);
  }
  return times;
}

// The segment the car is on at `elapsed`: points[index] -> points[index + 1],
// `frac` of the way along it. Binary search, since this runs every frame.
export function locate(times, elapsed) {
  const last = times.length - 1;
  if (last <= 0 || elapsed <= times[0]) return { index: 0, frac: 0 };
  if (elapsed >= times[last]) return { index: last, frac: 0 };

  let lo = 0;
  let hi = last;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (times[mid] <= elapsed) lo = mid;
    else hi = mid;
  }
  const span = times[hi] - times[lo];
  return { index: lo, frac: span ? (elapsed - times[lo]) / span : 0 };
}

// The car's x/y at `elapsed`, plus its heading in degrees (0 = pointing right,
// clockwise positive, matching SVG's rotate()).
export function carAt(points, times, elapsed) {
  const { index, frac } = locate(times, elapsed);
  const a = points[index];
  const b = points[index + 1] ?? a;
  // at the very end there's no next point, so face the way the last segment went
  const [from, to] = b === a && index > 0 ? [points[index - 1], a] : [a, b];
  return {
    index,
    x: a.x + (b.x - a.x) * frac,
    y: a.y + (b.y - a.y) * frac,
    angle: (Math.atan2(to.y - from.y, to.x - from.x) * 180) / Math.PI,
  };
}

const EARTH_RADIUS_M = 6_371_000;

function distanceMetres(a, b) {
  const rad = Math.PI / 180;
  const dLat = (b.latitude - a.latitude) * rad;
  const dLon = (b.longitude - a.longitude) * rad;
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a.latitude * rad) * Math.cos(b.latitude * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

// Speed in km/h around point `index`, estimated from GPS distance over time
// (the API doesn't send speed). Averaged over a few points either side so GPS
// jitter doesn't make it jump around. null if it can't be worked out.
export function speedKmhAt(positions, times, index, window = 3) {
  const from = Math.max(0, index - window);
  const to = Math.min(positions.length - 1, index + window);
  const dt = times[to] - times[from];
  if (to === from || !dt) return null;

  let metres = 0;
  for (let i = from; i < to; i++) metres += distanceMetres(positions[i], positions[i + 1]);
  return (metres / dt) * 3.6;
}

// 83.4 -> "1:23.4"
export function formatLapTime(seconds) {
  const tenths = Math.floor(Math.max(0, seconds) * 10);
  const minutes = Math.floor(tenths / 600);
  const secs = ((tenths % 600) / 10).toFixed(1).padStart(4, "0");
  return `${minutes}:${secs}`;
}
