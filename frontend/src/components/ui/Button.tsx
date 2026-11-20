import type { ButtonHTMLAttributes, ComponentPropsWithRef } from "react";
import { createLink } from "@tanstack/react-router";
import { cx } from "@utils/classNames";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "md" | "sm";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

// Figma "Button". Children are the label plus an optional lucide icon before it.
export default function Button({
  variant = "primary",
  size = "md",
  type = "button",
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(styles.button, styles[variant], styles[size], className)}
      {...props}
    />
  );
}

type ButtonAnchorProps = ComponentPropsWithRef<"a"> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

function ButtonAnchor({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonAnchorProps) {
  return <a className={cx(styles.button, styles[variant], styles[size], className)} {...props} />;
}

// A router link that looks like a Button, for actions that open another page.
// `disabled` renders it without an href.
export const ButtonLink = createLink(ButtonAnchor);
