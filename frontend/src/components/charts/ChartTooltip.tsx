import { seriesColor, type Series } from "./series";
import styles from "./ChartTooltip.module.css";

export type ChartTooltipRow = { series: Series; label: string; value: string };

type ChartTooltipProps = {
  // Where the cursor is on the lap, e.g. "50.0%".
  title: string;
  // One row per series under the cursor.
  rows: readonly ChartTooltipRow[];
};

// Figma "Chart Tooltip": the values under the chart cursor. Presentational; the chart positions it.
export default function ChartTooltip({ title, rows }: ChartTooltipProps) {
  return (
    <div className={styles.tooltip}>
      <p className={styles.title}>{title}</p>
      {rows.map((row) => (
        <p key={row.label} className={styles.row}>
          <span className={styles.swatch} style={{ background: seriesColor(row.series) }} />
          <span className={styles.label}>{row.label}</span>
          <span className={styles.value}>{row.value}</span>
        </p>
      ))}
    </div>
  );
}
