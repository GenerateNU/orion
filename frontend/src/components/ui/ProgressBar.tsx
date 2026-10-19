import { cx } from "@utils/classNames";
import styles from "./ProgressBar.module.css";

type ProgressBarProps = {
  // Accessible name, e.g. "Processing run 00d5d5a4…".
  label: string;
  // Fraction complete, 0–1. Leave it out while progress is unknown for an indeterminate bar.
  value?: number;
};

export default function ProgressBar({ label, value }: ProgressBarProps) {
  const percent =
    value === undefined ? undefined : Math.round(Math.min(Math.max(value, 0), 1) * 100);

  return (
    <div
      className={cx(styles.progress, percent === undefined && styles.indeterminate)}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
    >
      <div
        className={styles.fill}
        style={percent === undefined ? undefined : { width: `${percent}%` }}
      />
    </div>
  );
}
