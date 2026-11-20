import { useEffect, useRef, type ComponentPropsWithoutRef, type ReactNode } from "react";
import { Check } from "lucide-react";
import { cx } from "@utils/classNames";
import styles from "./Checkbox.module.css";

type CheckboxProps = Omit<ComponentPropsWithoutRef<"input">, "type"> & {
  // Text after the box. Without it, pass an aria-label.
  label?: ReactNode;
  // Figma "Mixed": some, not all, of a group is checked.
  indeterminate?: boolean;
};

// Figma "Checkbox": Checked (Off | On | Mixed). A native checkbox, restyled.
export default function Checkbox({
  label,
  indeterminate = false,
  className,
  ...props
}: CheckboxProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  // indeterminate exists only as a DOM property, not an attribute.
  useEffect(() => {
    if (inputRef.current) inputRef.current.indeterminate = indeterminate;
  }, [indeterminate]);

  return (
    <label className={cx(styles.checkbox, className)}>
      <span className={styles.box}>
        <input ref={inputRef} type="checkbox" className={styles.input} {...props} />
        <Check className={styles.check} aria-hidden="true" />
        <span className={styles.mixed} aria-hidden="true" />
      </span>
      {label}
    </label>
  );
}
