import { memo } from "react";
import RunStatusDot from "@components/runs/RunStatusDot";
import { formatDayLabel, formatRunTime, runName, type CalendarDay as Day } from "@utils/calendar";
import type { RunRow } from "@utils/runRows";
import { cx } from "@utils/classNames";
import styles from "./CalendarDay.module.css";

type CalendarDayProps = {
  day: Day;
  // That day's runs, earliest first.
  runs: readonly RunRow[];
  selected: boolean;
  isToday: boolean;
  // How many text lines fit under the date (MonthCalendar measures this).
  lineCount: number;
  onSelect: (day: string) => void;
};

// One cell of the Figma "Month grid": the date, then each run's start time with a
// status dot, as many as fit; when they don't all fit, the last line is "+N more".
// The whole cell is a button that opens the day's runs.
function CalendarDay({ day, runs, selected, isToday, lineCount, onSelect }: CalendarDayProps) {
  const visibleCount = runs.length <= lineCount ? runs.length : Math.max(0, lineCount - 1);
  const visible = runs.slice(0, visibleCount);
  const hidden = runs.length - visible.length;
  const runCount = runs.length === 1 ? "1 run" : `${runs.length} runs`;

  return (
    <button
      type="button"
      className={cx(styles.day, !day.inMonth && styles.outside, selected && styles.selected)}
      aria-pressed={selected}
      aria-current={isToday ? "date" : undefined}
      aria-label={`${formatDayLabel(day.day)}, ${runs.length ? runCount : "no runs"}`}
      onClick={() => onSelect(day.day)}
    >
      <span className={cx(styles.date, isToday && styles.today)}>{day.date.getDate()}</span>
      {visible.map((run) => (
        <span key={run.runId} className={styles.run} title={runName(run)}>
          <RunStatusDot status={run.status} />
          <span className={styles.time}>{formatRunTime(run)}</span>
        </span>
      ))}
      {hidden > 0 && lineCount > 0 && <span className={styles.more}>+{hidden} more</span>}
    </button>
  );
}

export default memo(CalendarDay);
