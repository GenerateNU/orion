import Checkbox from "@components/ui/Checkbox";
import { seriesColor, type Series } from "@components/charts/series";
import { cx } from "@utils/classNames";
import styles from "./LapRow.module.css";

type LapRowProps = {
  lap: number;
  // Lap time, e.g. "1:12.48".
  time: string;
  // Gap to the best lap, e.g. "+0.42".
  delta?: string;
  // The lap's chart color, shown in the left bar while it's selected or compared.
  series: Series;
  // The lap the dashboard is showing (Figma State=Selected).
  selected?: boolean;
  // Ticked for comparison (Figma State=Compared).
  compared?: boolean;
  onSelect?: () => void;
  onCompareChange?: (compared: boolean) => void;
};

// Figma "Lap Row": State (Default | Hover | Selected | Compared). Click the row to select the
// lap; tick the box to compare it.
export default function LapRow({
  lap,
  time,
  delta,
  series,
  selected = false,
  compared = false,
  onSelect,
  onCompareChange,
}: LapRowProps) {
  return (
    <div className={cx(styles.row, selected && styles.selected)}>
      <span
        className={styles.bar}
        style={selected || compared ? { background: seriesColor(series) } : undefined}
      />
      <button type="button" className={styles.main} aria-pressed={selected} onClick={onSelect}>
        <span className={styles.lap}>L{lap}</span>
        <span className={styles.time}>{time}</span>
        {delta && <span className={styles.delta}>{delta}</span>}
      </button>
      <Checkbox
        aria-label={`Compare lap ${lap}`}
        checked={compared}
        onChange={(event) => onCompareChange?.(event.target.checked)}
      />
    </div>
  );
}
