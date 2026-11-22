import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Button from "@components/ui/Button";
import IconButton from "@components/ui/IconButton";
import { formatMonthHeading, monthGrid, type DayKey, type MonthKey } from "@utils/calendar";
import type { RunRow } from "@utils/runRows";
import CalendarDay from "./CalendarDay";
import styles from "./MonthCalendar.module.css";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const NO_RUNS: readonly RunRow[] = [];
const WEEKS = 6;

// A day cell's fixed parts (CalendarDay.module.css): 8px padding and 1.5px border
// top and bottom, the date's 20px line, and a 4px gap before each 16px run line.
const CELL_CHROME = 2 * 8 + 20;
const LINE = 16 + 4;
// --space-2 (MonthCalendar.module.css); --space-1 at phone widths.
const gridGap = () => (window.matchMedia("(max-width: 768px)").matches ? 4 : 8);

// How many run lines fit under the date in a cell, from the grid's height.
function useLineCount() {
  const gridRef = useRef<HTMLDivElement>(null);
  const [lineCount, setLineCount] = useState(0);
  useEffect(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const observer = new ResizeObserver(() => {
      const rowHeight = (grid.clientHeight - (WEEKS - 1) * gridGap()) / WEEKS;
      setLineCount(Math.max(0, Math.floor((rowHeight - CELL_CHROME) / LINE)));
    });
    observer.observe(grid);
    return () => observer.disconnect();
  }, []);
  return [gridRef, lineCount] as const;
}

type MonthCalendarProps = {
  month: MonthKey;
  // Runs by local day, each day earliest first (utils/calendar groupRunsByDay).
  runsByDay: ReadonlyMap<DayKey, readonly RunRow[]>;
  selectedDay: DayKey | null;
  today: DayKey;
  onSelectDay: (day: DayKey) => void;
  onMonthChange: (delta: number) => void;
  onToday: () => void;
};

// Figma "Calendar": a month header with previous/next and Today, then a
// Monday-first grid of six weeks. Presentational: the view owns the state.
export default function MonthCalendar({
  month,
  runsByDay,
  selectedDay,
  today,
  onSelectDay,
  onMonthChange,
  onToday,
}: MonthCalendarProps) {
  const weeks = useMemo(() => monthGrid(month), [month]);
  const heading = formatMonthHeading(month);
  const [gridRef, lineCount] = useLineCount();

  return (
    <section className={styles.calendar} aria-labelledby="calendar-heading">
      <div className={styles.header}>
        <h2 id="calendar-heading" className={styles.heading} aria-live="polite">
          {heading}
        </h2>
        <IconButton variant="secondary" label="Previous month" onClick={() => onMonthChange(-1)}>
          <ChevronLeft />
        </IconButton>
        <IconButton variant="secondary" label="Next month" onClick={() => onMonthChange(1)}>
          <ChevronRight />
        </IconButton>
        <Button variant="ghost" size="sm" className={styles.today} onClick={onToday}>
          Today
        </Button>
      </div>

      <div className={styles.weekdays} aria-hidden="true">
        {WEEKDAYS.map((weekday) => (
          <span key={weekday}>{weekday}</span>
        ))}
      </div>

      <div ref={gridRef} className={styles.grid} role="group" aria-label={`Days of ${heading}`}>
        {weeks.flat().map((day) => (
          <CalendarDay
            key={day.day}
            day={day}
            runs={runsByDay.get(day.day) ?? NO_RUNS}
            selected={day.day === selectedDay}
            isToday={day.day === today}
            lineCount={lineCount}
            onSelect={onSelectDay}
          />
        ))}
      </div>
    </section>
  );
}
