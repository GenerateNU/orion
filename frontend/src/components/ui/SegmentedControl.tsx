import { useId } from "react";
import { cx } from "@utils/classNames";
import styles from "./SegmentedControl.module.css";

export type SegmentOption<T extends string> = { value: T; label: string };

type SegmentedControlProps<T extends string> = {
  options: readonly SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  // Accessible name of the group, e.g. "X axis".
  "aria-label": string;
  className?: string;
};

// Figma "Segmented Control": pick one of a few views. Native radios, so arrow keys work.
export default function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  "aria-label": ariaLabel,
  className,
}: SegmentedControlProps<T>) {
  const name = useId();

  return (
    <div role="radiogroup" aria-label={ariaLabel} className={cx(styles.control, className)}>
      {options.map((option) => (
        <label key={option.value} className={styles.segment}>
          <input
            type="radio"
            className="sr-only"
            name={name}
            value={option.value}
            checked={option.value === value}
            onChange={() => onChange(option.value)}
          />
          {option.label}
        </label>
      ))}
    </div>
  );
}
