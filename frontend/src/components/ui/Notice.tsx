import type { ReactNode } from "react";
import { cx } from "@utils/classNames";
import styles from "./Notice.module.css";

type NoticeProps = {
  tone: "warning" | "error";
  children: ReactNode;
};

export default function Notice({ tone, children }: NoticeProps) {
  return (
    <p className={cx(styles.notice, styles[tone])} role={tone === "error" ? "alert" : "status"}>
      {children}
    </p>
  );
}
