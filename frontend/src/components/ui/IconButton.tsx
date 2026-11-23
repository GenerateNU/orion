import type { ComponentPropsWithRef } from "react";
import { cx } from "@utils/classNames";
import Tooltip from "./Tooltip";
import styles from "./IconButton.module.css";

type IconButtonProps = ComponentPropsWithRef<"button"> & {
  // Accessible name, also shown as the tooltip (Figma: always pair with one).
  label: string;
  variant?: "ghost" | "secondary";
  // Toggle buttons: true renders Figma's "Active" state and sets aria-pressed.
  pressed?: boolean;
};

// Figma "Icon Button": a square, icon-only action. The child is a lucide icon.
export default function IconButton({
  label,
  variant = "ghost",
  pressed,
  type = "button",
  className,
  ...props
}: IconButtonProps) {
  return (
    <Tooltip content={label}>
      <button
        type={type}
        aria-label={label}
        aria-pressed={pressed}
        className={cx(styles.iconButton, styles[variant], className)}
        {...props}
      />
    </Tooltip>
  );
}
