import Button from "@components/ui/Button";
import { useMetrics } from "@hooks/useMetrics";
import {
  useDashboardActions,
  useDashboardRun,
  useSelectedLaps,
} from "@features/dashboard/state/useDashboard";
import styles from "./LapSelect.module.css";

// Steps through All laps → Lap 1 → … → Lap N, one at a time. The selection lives in
// the URL (?laps=): read it with useSelectedLaps; [] means all laps.
export default function LapSelect() {
  const { runId } = useDashboardRun();
  const { metrics, metricsIsLoading, metricsError } = useMetrics(runId);
  const selectedLaps = useSelectedLaps();
  const { selectLaps } = useDashboardActions();

  const lapNumbers = metrics?.laps.map((lap) => lap.lap_number) ?? [];
  // -1 is All laps, including a lap number this run doesn't have.
  const index = lapNumbers.indexOf(selectedLaps[0]);

  const goTo = (i: number) => selectLaps(i < 0 ? [] : [lapNumbers[i]]);

  const status = metricsIsLoading
    ? "Loading laps…"
    : metricsError
      ? "Laps unavailable"
      : lapNumbers.length === 0
        ? "No laps detected"
        : null;

  return (
    <div className={styles.root}>
      <span className={styles.label}>Lap</span>
      <Button
        variant="secondary"
        aria-label="Previous lap"
        disabled={status !== null || index < 0}
        onClick={() => goTo(index - 1)}
      >
        ▼
      </Button>
      <span className={styles.current} aria-live="polite">
        {status ?? (index < 0 ? "All laps" : `Lap ${lapNumbers[index]} of ${lapNumbers.length}`)}
      </span>
      <Button
        variant="secondary"
        aria-label="Next lap"
        disabled={status !== null || index === lapNumbers.length - 1}
        onClick={() => goTo(index + 1)}
      >
        ▲
      </Button>
    </div>
  );
}
