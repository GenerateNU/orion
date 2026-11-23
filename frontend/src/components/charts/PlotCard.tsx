import type { ReactNode } from "react";
import type { ChartTooltipRow } from "./ChartTooltip";
import { seriesColor } from "./series";
import styles from "./PlotCard.module.css";

type PlotCardProps = {
  // The signal, e.g. "Speed".
  title: string;
  unit?: string;
  // The value under the cursor: one string (Mode=Single, e.g. "33.6"), or one row per
  // compared lap (Mode=Compare), each in its series color.
  readout?: string | readonly ChartTooltipRow[];
  // IconButtons on the right, e.g. maximize and a ⋯ Menu.
  actions?: ReactNode;
  // The chart, e.g. a TimeSeriesChart with xAxis="track".
  children: ReactNode;
};

// Figma "Plot Card": Mode (Single | Compare). A chart with a header; the chart is the child.
export default function PlotCard({ title, unit, readout, actions, children }: PlotCardProps) {
  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        {unit && <span className={styles.unit}>{unit}</span>}
        <div className={styles.end}>
          {typeof readout === "string" ? (
            <span className={styles.readout}>{readout}</span>
          ) : (
            readout?.map(({ series, label, value }) => (
              <span key={label} className={styles.lap}>
                <span className={styles.swatch} style={{ background: seriesColor(series) }} />
                {label}
                <span className={styles.lapValue} style={{ color: seriesColor(series) }}>
                  {value}
                </span>
              </span>
            ))
          )}
          {actions}
        </div>
      </header>
      {children}
    </section>
  );
}
