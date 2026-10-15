// Turns GPS points into x/y coordinates inside a width x height box, so a lap can
// be drawn as a track without a real map underneath.
//
// Longitude is scaled by cos(latitude) so the shape isn't stretched sideways, the
// path is centred and fitted with `padding` on every side, and north stays up
// (a higher latitude gets a smaller y, since SVG's y grows downwards).

export function projectPositions(positions, width, height, padding = 0) {
  if (!positions.length) return [];

  const meanLat = positions.reduce((sum, p) => sum + p.latitude, 0) / positions.length;
  const kx = Math.cos((meanLat * Math.PI) / 180);

  const xs = positions.map((p) => p.longitude * kx);
  const ys = positions.map((p) => p.latitude);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const spanX = Math.max(...xs) - minX;
  const spanY = Math.max(...ys) - minY;

  // A zero span (one point, or a perfectly straight line) can't be scaled by;
  // if both are zero every point lands in the centre.
  const scale = Math.min(
    spanX ? (width - 2 * padding) / spanX : Infinity,
    spanY ? (height - 2 * padding) / spanY : Infinity
  );
  const k = Number.isFinite(scale) ? scale : 0;

  const offsetX = (width - spanX * k) / 2;
  const offsetY = (height - spanY * k) / 2;

  return positions.map((_, i) => ({
    x: offsetX + (xs[i] - minX) * k,
    y: height - (offsetY + (ys[i] - minY) * k),
  }));
}
