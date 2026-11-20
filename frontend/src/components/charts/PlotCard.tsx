import type { ReactNode } from "react";
import styles from "./PlotCard.module.css";

type PlotCardProps = {
  // The signal, e.g. "Speed".
  title: string;
  unit?: string;
  // The value under the cursor, e.g. "33.6"; in compare mode, SeriesChip-style values per lap.
  readout?: ReactNode;
  // IconButtons on the right, e.g. maximize and a ⋯ Menu.
  actions?: ReactNode;
  // The chart, e.g. a TimeSeriesChart.
  children: ReactNode;
};

// Figma "Plot Card": a chart with a header. The chart itself is the child.
export default function PlotCard({ title, unit, readout, actions, children }: PlotCardProps) {
  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        {unit && <span className={styles.unit}>{unit}</span>}
        <div className={styles.end}>
          {readout !== undefined && <span className={styles.readout}>{readout}</span>}
          {actions}
        </div>
      </header>
      {children}
    </section>
  );
}
