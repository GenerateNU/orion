/**
 * Helper functions for TrackMap component (SVG version)
 */

export type Position = [number, number]; // [x, y]

/**
 * Convert mouse position to time based on closest track point
 */
export function getTimeFromMouse(
  positions: Position[],
  time: number[],
  mouseX: number,
  mouseY: number,
): number {
  // Find closest point on track
  let minDist = Infinity;
  let closestIdx = 0;

  for (let i = 0; i < positions.length; i++) {
    const [x, y] = positions[i];
    const dist = Math.hypot(mouseX - x, mouseY - y);
    if (dist < minDist) {
      minDist = dist;
      closestIdx = i;
    }
  }

  // Interpolate time at closest index
  if (closestIdx === positions.length - 1) {
    return time[closestIdx];
  }

  // Simple linear interpolation between closest points
  const t = Math.min(1, minDist / 20); // Interpolate within 20px
  return time[closestIdx] + (time[closestIdx + 1] - time[closestIdx]) * t;
}

/**
 * Get car position by interpolating x,y directly
 */
export function getCarPosition(
  hoverTimeVal: number | null,
  positions: Position[],
  time: number[],
): { x: number; y: number } | null {
  if (hoverTimeVal === null) return null;

  // Find the two closest time points
  let idx = 0;
  for (let i = 0; i < time.length; i++) {
    if (time[i] <= hoverTimeVal) idx = i;
    else break;
  }

  if (idx === time.length - 1) {
    // At or past the end
    const [x, y] = positions[idx];
    return { x, y };
  }

  // Interpolate between idx and idx+1
  const t0 = time[idx];
  const t1 = time[idx + 1];
  const [x0, y0] = positions[idx];
  const [x1, y1] = positions[idx + 1];

  // Divide-by-zero guard
  if (t1 === t0) {
    return { x: x0, y: y0 };
  }

  // Linear interpolation factor
  const factor = (hoverTimeVal - t0) / (t1 - t0);
  const x = x0 + (x1 - x0) * factor;
  const y = y0 + (y1 - y0) * factor;

  return { x, y };
}

export interface Segment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

/**
 * Generate window line segments (committed or preview)
 */
export function generateSegments(
  windowStart: number,
  windowEnd: number,
  positions: Position[],
  time: number[],
): Segment[] {
  if (time.length === 0 || positions.length === 0) return [];

  const segments: Segment[] = [];

  for (let i = 0; i < positions.length - 1; i++) {
    const t_i = time[i];
    const t_next = time[i + 1];

    // Check if this segment overlaps the window
    if (t_next >= windowStart && t_i <= windowEnd) {
      const [x1, y1] = positions[i];
      const [x2, y2] = positions[i + 1];
      segments.push({ x1, y1, x2, y2 });
    }
  }

  return segments;
}
export function getMousePosOnSVG(
  event: React.MouseEvent<SVGSVGElement>,
  stageRef: React.RefObject<SVGSVGElement | null>,
): { x: number; y: number } | null {
  if (!stageRef.current) return null;
  const rect = stageRef.current.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}
