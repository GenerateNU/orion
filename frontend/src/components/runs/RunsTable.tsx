import { memo, type ReactNode } from "react";
import RunActions from "@components/runs/RunActions";
import StatusBadge from "@components/runs/StatusBadge";
import { formatDate, formatDuration } from "@utils/format";
import type { RunRow } from "@utils/runRows";
import styles from "./RunsTable.module.css";

const COLUMN_COUNT = 5;

type RunsTableProps = {
  rows: RunRow[];
  // Run id with a pipeline request in flight.
  pendingRunId: string | null;
  // Replaces the rows with a loading, error or empty state; the header stays.
  placeholder?: ReactNode;
  // Footer contents: a line of text on the left, pagination on the right.
  summary?: ReactNode;
  pagination?: ReactNode;
  onQueue: (runId: string) => void;
};

// Figma "Runs table". Presentational: rows and callbacks come from the view.
export default function RunsTable({ rows, pendingRunId, placeholder, summary, pagination, onQueue }: RunsTableProps) {
  return (
    <div className={styles.container}>
      <div className={styles.scroll}>
        <table className={styles.table}>
          <caption className="sr-only">Runs and their pipeline status</caption>
          <colgroup>
            <col className={styles.colRun} />
            <col className={styles.colDate} />
            <col className={styles.colDuration} />
            <col className={styles.colPipeline} />
            <col />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">Run</th>
              <th scope="col">Date</th>
              <th scope="col">Duration</th>
              <th scope="col">Pipeline</th>
              <th scope="col">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {placeholder ? (
              <tr>
                <td className={styles.placeholder} colSpan={COLUMN_COUNT}>
                  {placeholder}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <RunsTableRow
                  key={row.runId}
                  row={row}
                  isPending={row.runId === pendingRunId}
                  onQueue={onQueue}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
      {(summary || pagination) && (
        <div className={styles.footer}>
          {summary && <p className={styles.summary}>{summary}</p>}
          {pagination}
        </div>
      )}
    </div>
  );
}

type RunsTableRowProps = {
  row: RunRow;
  isPending: boolean;
  onQueue: (runId: string) => void;
};

// Memoised so a pending/page change re-renders only the rows it touches.
const RunsTableRow = memo(function RunsTableRow({ row, isPending, onQueue }: RunsTableRowProps) {
  return (
    <tr>
      <th scope="row" className={styles.run} title={row.runId}>
        {row.runId}
      </th>
      <td>{formatDate(row.time)}</td>
      <td className={styles.duration}>{formatDuration(row.durationS)}</td>
      <td>
        <StatusBadge status={row.status} detail={row.latestJob?.error ?? undefined} />
      </td>
      <td className={styles.actions}>
        <RunActions row={row} isPending={isPending} onQueue={onQueue} />
      </td>
    </tr>
  );
});
