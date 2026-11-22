import { X } from "lucide-react";
import DayRunRow from "@components/runs/DayRunRow";
import SelectedRunDetails from "@components/runs/SelectedRunDetails";
import EmptyState from "@components/ui/EmptyState";
import IconButton from "@components/ui/IconButton";
import { formatDayHeading, type DayKey } from "@utils/calendar";
import type { RunRow } from "@utils/runRows";
import styles from "./DayRunsPanel.module.css";

type DayRunsPanelProps = {
  day: DayKey;
  // The day's runs, earliest first.
  runs: readonly RunRow[];
  selectedRunId: string | null;
  pendingRunId: string | null;
  onSelectRun: (runId: string) => void;
  onQueue: (runId: string) => void;
  onClose: () => void;
};

// Figma "Runs on the selected day": the side panel that opens when a calendar day
// is clicked. Lists the day's runs by time; the selected one shows its details.
export default function DayRunsPanel({
  day,
  runs,
  selectedRunId,
  pendingRunId,
  onSelectRun,
  onQueue,
  onClose,
}: DayRunsPanelProps) {
  const selected = runs.find((run) => run.runId === selectedRunId) ?? null;
  const count = runs.length === 1 ? "1 run" : `${runs.length} runs`;

  return (
    <aside className={styles.panel} aria-labelledby="day-panel-heading">
      <div className={styles.header}>
        <div className={styles.text}>
          <h2 id="day-panel-heading" className={styles.heading}>
            {formatDayHeading(day)}
          </h2>
          {runs.length > 0 && (
            <p className={styles.description}>{count} · click one to select it</p>
          )}
        </div>
        <IconButton label="Close day" onClick={onClose}>
          <X />
        </IconButton>
      </div>

      {runs.length === 0 ? (
        <EmptyState message="No runs on this day." />
      ) : (
        <ul className={styles.runs} aria-label={`Runs on ${formatDayHeading(day)}`}>
          {runs.map((run) => (
            <li key={run.runId}>
              <DayRunRow row={run} selected={run.runId === selectedRunId} onSelect={onSelectRun} />
            </li>
          ))}
        </ul>
      )}

      {selected && (
        <SelectedRunDetails
          row={selected}
          isPending={selected.runId === pendingRunId}
          onQueue={onQueue}
        />
      )}
    </aside>
  );
}
