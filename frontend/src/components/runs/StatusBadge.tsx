import { Check, Clock, CircleX, LoaderCircle, type LucideIcon } from "lucide-react";
import type { RunStatus } from "@utils/runRows";
import { cx } from "@utils/classNames";
import styles from "./StatusBadge.module.css";

const STATUS: Record<RunStatus, { label: string; className: string; Icon?: LucideIcon }> = {
  loaded: { label: "Ready", className: styles.loaded, Icon: Check },
  processing: { label: "Processing", className: styles.processing, Icon: LoaderCircle },
  queued: { label: "Queued", className: styles.queued, Icon: Clock },
  failed: { label: "Failed", className: styles.failed, Icon: CircleX },
  // Figma draws a dot instead of an icon.
  "not-processed": { label: "Not processed", className: styles.notProcessed },
};

type StatusBadgeProps = {
  status: RunStatus;
  // Extra context as a tooltip, e.g. the pipeline error of a failed run.
  detail?: string;
};

// Figma "Status Badge": the pipeline status of a run.
export default function StatusBadge({ status, detail }: StatusBadgeProps) {
  const { label, className, Icon } = STATUS[status];
  return (
    <span className={cx(styles.badge, className)} title={detail}>
      {Icon ? <Icon aria-hidden="true" /> : <span className={styles.dot} aria-hidden="true" />}
      {label}
    </span>
  );
}
