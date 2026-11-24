import { X } from "lucide-react";
import { seriesColor, type Series } from "./series";
import styles from "./SeriesChip.module.css";

type SeriesChipProps = {
  series: Series;
  label: string;
  // Shows the × button; leave out for a chip that can't be removed.
  onRemove?: () => void;
};

// Figma "Series Chip": Series (1–8). Names one line of a chart, e.g. a compared lap.
export default function SeriesChip({ series, label, onRemove }: SeriesChipProps) {
  return (
    <span className={styles.chip}>
      <span className={styles.swatch} style={{ background: seriesColor(series) }} />
      {label}
      {onRemove && (
        <button
          type="button"
          className={styles.remove}
          aria-label={`Remove ${label}`}
          onClick={onRemove}
        >
          <X aria-hidden="true" />
        </button>
      )}
    </span>
  );
}
