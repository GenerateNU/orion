import { useEffect, useState } from "react";
import type { Size } from "@features/dashboard/utils/trackView";

// The element's content-box size in CSS pixels, kept current by a ResizeObserver.
// Pass `ref` as the element's ref; `size` is null until it has mounted.
export function useElementSize<T extends HTMLElement>(): [
  ref: (element: T | null) => void,
  size: Size | null,
] {
  const [element, setElement] = useState<T | null>(null);
  const [size, setSize] = useState<Size | null>(null);

  useEffect(() => {
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setSize((prev) =>
        prev?.width === width && prev.height === height ? prev : { width, height },
      );
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);

  return [setElement, size];
}
