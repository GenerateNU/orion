import { cx } from "@utils/classNames";
import styles from "./StatTile.module.css";

type StatTileProps = {
  label: string;
  // The number, e.g. "1:12.48".
  value: string;
  // Compared to a reference, e.g. { text: "−0.42s vs best", better: true }: green or red.
  delta?: { text: string; better: boolean };
  // A gold note instead of a delta, e.g. "Session best".
  note?: string;
  // "sm": tighter padding, no min-width and a Data/Readout M value, so several fit
  // side by side in a narrow panel.
  size?: "md" | "sm";
};

// Figma "Stat Tile": Delta (Better | Worse | None). One headline number.
export default function StatTile({ label, value, delta, note, size = "md" }: StatTileProps) {
  return (
    <div className={cx(styles.tile, size === "sm" && styles.sm)}>
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>{value}</p>
      {delta && (
        <p className={cx(styles.delta, delta.better ? styles.better : styles.worse)}>
          {delta.text}
        </p>
      )}
      {note && <p className={styles.note}>{note}</p>}
    </div>
  );
}
