import type { ReactNode } from "react";
import { CircleX, Info, TriangleAlert } from "lucide-react";
import { cx } from "@utils/classNames";
import styles from "./Notice.module.css";

type NoticeTone = "error" | "warning" | "info";

type NoticeProps = {
  tone: NoticeTone;
  // Bold first line; children follow as the description.
  title?: string;
  children: ReactNode;
};

const ICON = { error: CircleX, warning: TriangleAlert, info: Info };

// Figma "Alert Banner": Type (Error | Warning | Info). An inline message about the page.
export default function Notice({ tone, title, children }: NoticeProps) {
  const Icon = ICON[tone];
  return (
    <div className={cx(styles.notice, styles[tone])} role={tone === "error" ? "alert" : "status"}>
      <Icon className={styles.icon} aria-hidden="true" />
      <div className={styles.text}>
        {title && <p className={styles.title}>{title}</p>}
        <p className={title ? styles.description : styles.message}>{children}</p>
      </div>
    </div>
  );
}
