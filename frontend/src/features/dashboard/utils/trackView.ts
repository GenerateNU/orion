import type { Bounds, Vec2 } from "@features/dashboard/utils/trackGeometry";

export type Size = { width: number; height: number };

// Maps track metres to CSS pixels: one scale for both axes (the track keeps its
// shape), centred in the viewport, north up.
export type ViewTransform = {
  scale: number; // px per metre
  offsetX: number;
  offsetY: number;
};

// null when the viewport is too small to fit anything inside the padding.
export function fitTransform(bounds: Bounds, size: Size, padding: number): ViewTransform | null {
  const width = size.width - 2 * padding;
  const height = size.height - 2 * padding;
  if (width <= 0 || height <= 0) return null;

  const scale = Math.min(
    width / Math.max(bounds.maxX - bounds.minX, 1),
    height / Math.max(bounds.maxY - bounds.minY, 1),
  );
  return {
    scale,
    offsetX: size.width / 2 - ((bounds.minX + bounds.maxX) / 2) * scale,
    offsetY: size.height / 2 + ((bounds.minY + bounds.maxY) / 2) * scale,
  };
}

export const toScreen = (view: ViewTransform, point: Vec2): Vec2 => ({
  x: view.offsetX + point.x * view.scale,
  y: view.offsetY - point.y * view.scale,
});

export const toWorld = (view: ViewTransform, point: Vec2): Vec2 => ({
  x: (point.x - view.offsetX) / view.scale,
  y: (view.offsetY - point.y) / view.scale,
});
