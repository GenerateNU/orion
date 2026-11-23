import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cx } from "@utils/classNames";
import styles from "./Toggle.module.css";

type ToggleProps = Omit<ComponentPropsWithoutRef<"input">, "type"> & {
  // Text after the switch. Without it, pass an aria-label.
  label?: ReactNode;
};

// Figma "Toggle": On (true | false). A native checkbox with the switch role.
export default function Toggle({ label, className, ...props }: ToggleProps) {
  return (
    <label className={cx(styles.toggle, className)}>
      <input type="checkbox" role="switch" className={styles.input} {...props} />
      {label}
    </label>
  );
}
