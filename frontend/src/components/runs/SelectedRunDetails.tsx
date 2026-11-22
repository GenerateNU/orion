import { ArrowRight, RefreshCw } from "lucide-react";
import RunActions from "@components/runs/RunActions";
import Button, { ButtonLink } from "@components/ui/Button";
import StatTile from "@components/ui/StatTile";
import { useRunLapSummary } from "@hooks/useRuns";
import { runName } from "@utils/calendar";
import { formatDuration, formatLapTime } from "@utils/format";
import type { RunRow } from "@utils/runRows";
import styles from "./SelectedRunDetails.module.css";

type SelectedRunDetailsProps = {
  row: RunRow;
  // A pipeline request for this run is in flight.
  isPending: boolean;
  onQueue: (runId: string) => void;
};

// Figma "Selected run": the run's name (with Re-run once it's loaded), its headline
// numbers, then its main action: Open dashboard when loaded, otherwise RunActions'
// Queue/Retry pipeline, progress bar or queue position.
export default function SelectedRunDetails({ row, isPending, onQueue }: SelectedRunDetailsProps) {
  // Only runs in OrionDB have laps; others would 404.
  const { lapSummary, lapSummaryIsLoading, lapSummaryError } = useRunLapSummary(row.runId, {
    enabled: row.canOpen,
  });
  const lapsNote = lapSummaryIsLoading
    ? "Loading…"
    : lapSummaryError
      ? "Couldn't load laps"
      : !row.canOpen || lapSummary?.lap_count === 0
        ? "No laps detected"
        : undefined;

  return (
    <section className={styles.details} aria-labelledby="selected-run-heading">
      <div className={styles.header}>
        <h3 id="selected-run-heading" className={styles.heading} title={row.runId}>
          {runName(row)}
        </h3>
        {row.status === "loaded" && (
          <Button
            variant="secondary"
            size="sm"
            disabled={isPending}
            aria-label={`${isPending ? "Queuing pipeline" : "Re-run pipeline"} for ${runName(row)}`}
            onClick={() => onQueue(row.runId)}
          >
            <RefreshCw aria-hidden="true" />
            {isPending ? "Queuing…" : "Re-run"}
          </Button>
        )}
      </div>
      <div className={styles.stats}>
        <StatTile size="sm" label="Duration" value={formatDuration(row.durationS)} />
        <StatTile
          size="sm"
          label="Laps"
          value={lapSummary ? String(lapSummary.lap_count) : "—"}
          note={lapsNote}
        />
        <StatTile
          size="sm"
          label="Best lap"
          value={formatLapTime(lapSummary?.best_lap_time_s ?? null)}
          note={lapSummary?.best_lap_id != null ? `Lap ${lapSummary.best_lap_id}` : undefined}
        />
      </div>
      <div className={styles.action}>
        {row.status === "loaded" ? (
          <ButtonLink
            to="/runs/$runId/dashboard"
            params={{ runId: row.runId }}
            disabled={!row.canOpen}
            aria-label={`Open dashboard for ${runName(row)}`}
          >
            Open dashboard <ArrowRight aria-hidden="true" />
          </ButtonLink>
        ) : (
          <RunActions row={row} isPending={isPending} onQueue={onQueue} />
        )}
      </div>
    </section>
  );
}
