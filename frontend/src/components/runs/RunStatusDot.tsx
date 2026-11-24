import type { RunStatus } from "@utils/runRows";
import { cx } from "@utils/classNames";
import styles from "./RunStatusDot.module.css";

// A 6px dot in the run's status color (Figma calendar "Ellipse"): the compact form
// of StatusBadge, for places too small for the label.
export default function RunStatusDot({ status }: { status: RunStatus }) {
  return <span className={cx(styles.dot, styles[status])} aria-hidden="true" />;
}
