import type { ReactNode } from "react";
import { cx } from "@utils/classNames";
import styles from "./EmptyState.module.css";

type EmptyStateProps = {
  message: string;
  // With a title it's Figma's dashed card, for a whole empty page; without, one
  // muted line, for inside a panel (a chart, the track map).
  title?: string;
  // A lucide icon, shown in a red tile above the title.
  icon?: ReactNode;
  // A call to action below the message, e.g. a primary Button.
  action?: ReactNode;
};

// Figma "Empty State": nothing to show yet, and what to do about it.
export default function EmptyState({ message, title, icon, action }: EmptyStateProps) {
  return (
    <div className={cx(styles.empty, title && styles.card)}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {title && <p className={styles.title}>{title}</p>}
      <p className={styles.message}>{message}</p>
      {action}
    </div>
  );
}
