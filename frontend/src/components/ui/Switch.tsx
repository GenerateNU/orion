import type { InputHTMLAttributes, ReactNode } from "react";
import { cx } from "@utils/classNames";
import styles from "./Switch.module.css";

type SwitchProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "role" | "onChange"> & {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label: ReactNode;
};

// An on/off switch with a visible label. It's a native checkbox with
// role="switch", so keyboard and screen readers work as usual; the track and
// thumb only draw its state. Use this for every switch so they all match.
export default function Switch({
  checked,
  onCheckedChange,
  label,
  className,
  disabled,
  ...props
}: SwitchProps) {
  return (
    <label className={cx(styles.switch, disabled && styles.disabled, className)}>
      <input
        type="checkbox"
        role="switch"
        className={styles.input}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onCheckedChange(e.target.checked)}
        {...props}
      />
      <span className={styles.track} aria-hidden="true">
        <span className={styles.thumb} />
      </span>
      {label}
    </label>
  );
}
