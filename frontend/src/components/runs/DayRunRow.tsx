import { memo } from "react";
import { Info, Route } from "lucide-react";
import StatusBadge from "@components/runs/StatusBadge";
import Tooltip from "@components/ui/Tooltip";
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

// Figma "Run Row" in the day panel: route icon, date-time (full run id in an ⓘ
// tooltip) over the short run name, duration, pipeline status. Clicking it selects
// the run.
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
        <span className={styles.title}>
          <span className={styles.time}>{formatRunDateTime(row)}</span>
          {/* Hover-only: a focusable trigger can't sit inside the row's <button>, so
              screen readers get the full id from the sr-only text instead. */}
          <Tooltip content={<span className={styles.runId}>{row.runId}</span>}>
            <span className={styles.info} aria-hidden="true">
              <Info />
            </span>
          </Tooltip>
        </span>
        <span className={styles.shortName} aria-hidden="true">
          {runName(row)}
        </span>
        <span className="sr-only">, run {row.runId}</span>
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
