import type { ButtonHTMLAttributes, ComponentPropsWithRef } from "react";
import { createLink } from "@tanstack/react-router";
import { cx } from "@utils/classNames";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export default function Button({ variant = "primary", type = "button", className, ...props }: ButtonProps) {
  return <button type={type} className={cx(styles.button, styles[variant], className)} {...props} />;
}

type ButtonAnchorProps = ComponentPropsWithRef<"a"> & {
  variant?: ButtonVariant;
};

function ButtonAnchor({ variant = "primary", className, ...props }: ButtonAnchorProps) {
  return <a className={cx(styles.button, styles[variant], className)} {...props} />;
}

// A router link that looks like a Button, for actions that open another page.
// `disabled` renders it without an href.
export const ButtonLink = createLink(ButtonAnchor);
