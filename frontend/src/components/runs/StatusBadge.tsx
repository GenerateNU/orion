import type { RunStatus } from "@utils/runRows";
import { cx } from "@utils/classNames";
import styles from "./StatusBadge.module.css";

const STATUS_LABEL: Record<RunStatus, string> = {
  loaded: "Loaded",
  processing: "Processing",
  queued: "Queued",
  "not-processed": "Not processed",
  failed: "Failed",
};

const STATUS_CLASS: Record<RunStatus, string> = {
  loaded: styles.loaded,
  processing: styles.processing,
  queued: styles.queued,
  "not-processed": styles.notProcessed,
  failed: styles.failed,
};

type StatusBadgeProps = {
  status: RunStatus;
  // Extra context as a tooltip, e.g. the pipeline error of a failed run.
  detail?: string;
};

// Figma "StatusBadge": the pipeline status of a run.
export default function StatusBadge({ status, detail }: StatusBadgeProps) {
  return (
    <span className={cx(styles.badge, STATUS_CLASS[status])} title={detail}>
      <span className={styles.dot} aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}
