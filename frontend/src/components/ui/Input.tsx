import { useId, type ComponentPropsWithRef, type ReactNode } from "react";
import { cx } from "@utils/classNames";
import styles from "./Field.module.css";
import inputStyles from "./Input.module.css";

type InputProps = ComponentPropsWithRef<"input"> & {
  // Shown above the field. Without it, pass an aria-label.
  label?: string;
  helper?: ReactNode;
  // Replaces the helper, in red, and marks the field invalid.
  error?: string;
  // A lucide icon at the start of the field, e.g. <Calendar />.
  icon?: ReactNode;
  // "timestamp" sets the value in the monospaced data font.
  variant?: "text" | "timestamp";
};

// Figma "Input": Type (Text | Timestamp) × State (Default | Focus | Error | Disabled).
export default function Input({
  label,
  helper,
  error,
  icon,
  variant = "text",
  className,
  id,
  ...props
}: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const note = error ?? helper;

  return (
    <div className={cx(styles.wrapper, className)}>
      {label && (
        <label className={styles.label} htmlFor={inputId}>
          {label}
        </label>
      )}
      <div className={styles.field}>
        {icon}
        <input
          id={inputId}
          className={cx(inputStyles.input, variant === "timestamp" && inputStyles.timestamp)}
          aria-invalid={error ? true : undefined}
          aria-describedby={note ? `${inputId}-note` : undefined}
          {...props}
        />
      </div>
      {note && (
        <p id={`${inputId}-note`} className={cx(styles.helper, error && styles.error)}>
          {note}
        </p>
      )}
    </div>
  );
}
