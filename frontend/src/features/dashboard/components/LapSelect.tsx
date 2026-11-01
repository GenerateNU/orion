import { useEffect, useRef, useState } from "react";
import Button from "@components/ui/Button";
import { cx } from "@utils/classNames";
import { describeError } from "@utils/describeError";
import { formatDuration } from "@utils/format";
import { useLaps } from "@features/dashboard/data/useDashboardData";
import {
  useDashboardActions,
  useDashboardRun,
  useSelectedLaps,
} from "@features/dashboard/state/useDashboard";
import styles from "./LapSelect.module.css";

// Multi-select of the run's laps. The selection lives in the URL (?laps=): read
// with useSelectedLaps, changed with selectLaps, never copied into state here.
export default function LapSelect() {
  const { timeline } = useDashboardRun();
  const { laps, lapsIsLoading, lapsError } = useLaps();
  const urlLaps = useSelectedLaps();
  const { selectLaps, setHoverLap } = useDashboardActions();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Lap ids in the URL that this run doesn't have are ignored.
  const selected = urlLaps.filter((id) => laps?.some((lap) => lap.id === id));

  // Close on a click outside; stop highlighting a lap once closed.
  useEffect(() => {
    if (!open) {
      setHoverLap(null);
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open, setHoverLap]);

  const status = lapsIsLoading
    ? "Loading laps…"
    : lapsError
      ? "Laps unavailable"
      : !timeline || !laps || laps.length === 0
        ? "No laps detected"
        : null;

  const allIds = laps?.map((lap) => lap.id) ?? [];
  const allSelected = allIds.length > 0 && selected.length === allIds.length;

  const summary = allSelected
    ? "All laps"
    : selected.length === 0
      ? "No laps selected"
      : `${selected.length === 1 ? "Lap" : "Laps"} ${selected.join(", ")}`;

  // Sends the whole new list, so lap ids the run doesn't have drop out of the URL.
  const toggle = (id: number) =>
    selectLaps(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);

  return (
    <div
      ref={rootRef}
      className={styles.root}
      onKeyDown={(event) => {
        if (event.key === "Escape") setOpen(false);
      }}
    >
      <span className={styles.label}>Laps</span>
      <button
        type="button"
        className={styles.trigger}
        aria-expanded={open}
        disabled={status !== null}
        title={lapsError ? describeError(lapsError) : undefined}
        onClick={() => setOpen((isOpen) => !isOpen)}
      >
        {status ?? summary} <span aria-hidden="true">▾</span>
      </button>
      <Button variant="secondary" disabled={selected.length === 0} onClick={() => selectLaps([])}>
        Clear
      </Button>

      {open && laps && (
        <fieldset className={styles.list} onMouseLeave={() => setHoverLap(null)}>
          <legend className="sr-only">Laps to show</legend>
          <label
            className={cx(styles.option, styles.selectAll)}
            onMouseEnter={() => setHoverLap(null)}
          >
            <input
              type="checkbox"
              checked={allSelected}
              ref={(input) => {
                if (input) input.indeterminate = selected.length > 0 && !allSelected;
              }}
              onChange={() => selectLaps(allSelected ? [] : allIds)}
              onFocus={() => setHoverLap(null)}
            />
            Select all
          </label>
          {laps.map((lap) => (
            <label key={lap.id} className={styles.option} onMouseEnter={() => setHoverLap(lap.id)}>
              <input
                type="checkbox"
                checked={selected.includes(lap.id)}
                onChange={() => toggle(lap.id)}
                onFocus={() => setHoverLap(lap.id)}
              />
              Lap {lap.id}
              <span className={styles.duration}>
                {formatDuration((lap.window[1] - lap.window[0]) / 1000)}
              </span>
            </label>
          ))}
        </fieldset>
      )}
    </div>
  );
}
