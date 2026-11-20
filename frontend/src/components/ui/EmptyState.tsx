import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

type EmptyStateProps = {
  message: string;
  title?: string;
  // A lucide icon, shown in a red tile above the title.
  icon?: ReactNode;
  // A call to action below the message, e.g. a primary Button.
  action?: ReactNode;
};

// Figma "Empty State": nothing to show yet, and what to do about it.
export default function EmptyState({ message, title, icon, action }: EmptyStateProps) {
  return (
    <div className={styles.empty}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {title && <p className={styles.title}>{title}</p>}
      <p className={styles.message}>{message}</p>
      {action}
    </div>
  );
}
