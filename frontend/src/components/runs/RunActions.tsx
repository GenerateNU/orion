import Button, { ButtonLink } from "@components/ui/Button";
import ProgressBar from "@components/ui/ProgressBar";
import type { RunRow } from "@utils/runRows";
import { cx } from "@utils/classNames";
import styles from "./RunActions.module.css";

type RunActionsProps = {
  row: RunRow;
  // A pipeline request for this run is in flight.
  isPending: boolean;
  onQueue: (runId: string) => void;
};

// The action column of the Runs table: what the user can do next, by status.
export default function RunActions({ row, isPending, onQueue }: RunActionsProps) {
  switch (row.status) {
    case "processing":
      // The backend reports no progress yet, so the bar is indeterminate.
      return (
        <div className={cx(styles.actions, styles.stacked)}>
          {row.latestJob && <span className={styles.meta}>Job #{row.latestJob.id}</span>}
          <ProgressBar label={`Processing run ${row.runId}`} />
        </div>
      );

    case "queued":
      return (
        <div className={styles.actions}>
          {row.queuePosition !== null && (
            <span className={styles.meta}>#{row.queuePosition} in queue</span>
          )}
        </div>
      );

    case "not-processed":
    case "failed": {
      const label = isPending ? "Queuing…" : row.status === "failed" ? "Retry pipeline" : "Queue pipeline";
      return (
        <Button
          variant={row.status === "failed" ? "secondary" : "primary"}
          disabled={isPending}
          aria-label={`${label} for run ${row.runId}`}
          onClick={() => onQueue(row.runId)}
        >
          {label}
        </Button>
      );
    }

    case "loaded":
      return (
        <ButtonLink
          variant="secondary"
          to="/runs/$runId/dashboard"
          params={{ runId: row.runId }}
          disabled={!row.canOpen}
          aria-label={`Open dashboard for run ${row.runId}`}
        >
          Open dashboard <span aria-hidden="true">→</span>
        </ButtonLink>
      );
  }
}
