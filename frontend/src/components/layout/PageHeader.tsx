import type { ReactNode } from "react";
import { cx } from "@utils/classNames";
import styles from "./PageHeader.module.css";

type PageHeaderProps = {
  title: string;
  description?: ReactNode;
  // Shown beside the title, e.g. a StatusBadge.
  badge?: ReactNode;
  // Right-aligned page actions.
  actions?: ReactNode;
  // "page": a section title (Runs). "entity": a monospace identifier (a run id).
  variant?: "page" | "entity";
};

// The <h1> of every view.
export default function PageHeader({
  title,
  description,
  badge,
  actions,
  variant = "page",
}: PageHeaderProps) {
  return (
    <header className={cx(styles.header, variant === "entity" && styles.entity)}>
      <div className={styles.text}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{title}</h1>
          {badge}
        </div>
        {description && <p className={styles.description}>{description}</p>}
      </div>
      {actions && <div>{actions}</div>}
    </header>
  );
}
