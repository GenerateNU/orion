import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { cx } from "@utils/classNames";
import styles from "./ResizeHandle.module.css";

// Arrow-key step, in px.
const KEY_STEP = 16;

type ResizeHandleProps = {
  // Accessible name, e.g. "Resize day panel".
  label: string;
  // The size it controls, for screen readers (aria-valuenow/min/max), in px. Leave
  // out while it's unknown (e.g. still the CSS default).
  value?: number;
  min: number;
  max: number;
  // A drag or key press is starting: remember the size to resize from.
  onResizeStart: () => void;
  // Horizontal distance in px since onResizeStart (negative is left).
  onResize: (deltaX: number) => void;
  // Double-click: back to the default size.
  onReset?: () => void;
  className?: string;
};

// A vertical drag handle between two panes (WAI-ARIA window splitter): drag it, or
// focus it and use ←/→. The parent owns the size and clamps it.
export default function ResizeHandle({
  label,
  value,
  min,
  max,
  onResizeStart,
  onResize,
  onReset,
  className,
}: ResizeHandleProps) {
  const startX = useRef<number | null>(null);

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    // No text selection while dragging; keep getting moves outside the handle.
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    startX.current = event.clientX;
    onResizeStart();
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (startX.current !== null) onResize(event.clientX - startX.current);
  };

  const handlePointerEnd = () => {
    startX.current = null;
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = { ArrowLeft: -KEY_STEP, ArrowRight: KEY_STEP }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    onResizeStart();
    onResize(step);
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={value === undefined ? undefined : Math.round(value)}
      aria-valuemin={Math.round(min)}
      aria-valuemax={Math.round(max)}
      tabIndex={0}
      title="Drag to resize, double-click to reset"
      className={cx(styles.handle, className)}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onKeyDown={handleKeyDown}
      onDoubleClick={onReset}
    />
  );
}
