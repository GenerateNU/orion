import { memo } from "react";
import { Route } from "lucide-react";
import StatusBadge from "@components/runs/StatusBadge";
import { formatRunDateTime, runName } from "@utils/calendar";
import { formatDuration } from "@utils/format";
import type { RunRow } from "@utils/runRows";
import { cx } from "@utils/classNames";
import styles from "./DayRunRow.module.css";

type DayRunRowProps = {
  row: RunRow;
  selected: boolean;
  onSelect: (runId: string) => void;
};

// Figma "Run Row" in the day panel: route icon, date-time and run name, duration,
// pipeline status. Clicking it selects the run.
function DayRunRow({ row, selected, onSelect }: DayRunRowProps) {
  return (
    <button
      type="button"
      className={cx(styles.row, selected && styles.selected)}
      aria-pressed={selected}
      onClick={() => onSelect(row.runId)}
    >
      <span className={styles.icon} aria-hidden="true">
        <Route />
      </span>
      <span className={styles.name}>
        <span className={styles.time}>{formatRunDateTime(row)}</span>
        <span className={styles.id} title={row.runId}>
          {runName(row)}
        </span>
      </span>
      <span className={styles.duration}>
        <span className="sr-only">Duration </span>
        {formatDuration(row.durationS)}
      </span>
      <span className={styles.status}>
        <StatusBadge status={row.status} detail={row.latestJob?.error ?? undefined} />
      </span>
    </button>
  );
}

export default memo(DayRunRow);
