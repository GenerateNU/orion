import { useEffect, useRef } from "react";
import Button from "@components/ui/Button";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import { useLaps } from "@features/dashboard/data/useDashboardData";
import { useDashboardActions, useSelectedLaps } from "@features/dashboard/state/useDashboard";
import { lapColor } from "@features/dashboard/utils/laps";
import { cx } from "@utils/classNames";
import { formatDuration } from "@utils/format";
import styles from "./LapSelector.module.css";

// The run's laps as a horizontally scrolling row of toggles above the track map,
// each with its lap color and lap time. No lap is selected until the user picks
// some (or uses LapActions, in the panel header).
export function LapSelector() {
  const { laps, lapsIsLoading, lapsError } = useLaps();
  const selected = useSelectedLaps();
  const { toggleLap, setHoverLap } = useDashboardActions();

  // A mouse wheel scrolls the row sideways. Attached directly, not as onWheel,
  // because React's wheel listeners are passive and can't stop the page scrolling.
  const rowRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const row = rowRef.current;
    if (!row) return;
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      if (row.scrollWidth <= row.clientWidth) return;
      e.preventDefault();
      row.scrollLeft += e.deltaY;
    };
    row.addEventListener("wheel", onWheel, { passive: false });
    return () => row.removeEventListener("wheel", onWheel);
  }, [laps]);

  if (lapsIsLoading) return <LoadingState message="Loading laps…" />;
  if (lapsError) return <ErrorState error={lapsError} />;
  if (!laps || laps.length === 0) return <EmptyState message="No laps in this run." />;

  const isSelected = (lapId: number) => selected.includes(lapId);

  return (
    <div className={styles.selector} role="group" aria-label="Laps">
      <div ref={rowRef} className={styles.laps}>
        {laps.map(({ id, window: [start, end] }) => (
          <button
            key={id}
            type="button"
            className={cx(styles.lap, !isSelected(id) && styles.off)}
            aria-pressed={isSelected(id)}
            // A click mustn't focus the lap: the browser would scroll the row to
            // show all of it. Keyboard focus (Tab) still works.
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => toggleLap(id)}
            onPointerEnter={() => setHoverLap(id)}
            onPointerLeave={() => setHoverLap(null)}
          >
            <span
              className={styles.dot}
              style={isSelected(id) ? { background: lapColor(id, selected) } : undefined}
              aria-hidden="true"
            />
            Lap {id}
            <span className={styles.time}>({formatDuration((end - start) / 1000)})</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// Select all / Clear for the lap row, shown beside the "Track position" heading.
export function LapActions() {
  const { laps } = useLaps();
  const selected = useSelectedLaps();
  const { selectLaps } = useDashboardActions();
  if (!laps || laps.length === 0) return null;

  return (
    <div className={styles.actions}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => selectLaps(laps.map((lap) => lap.id))}
        disabled={selected.length === laps.length}
      >
        Select all
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => selectLaps([])}
        disabled={selected.length === 0}
      >
        Clear
      </Button>
    </div>
  );
}
