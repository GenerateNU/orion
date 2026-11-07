import { useMemo } from "react";
import { useRunLapProgress } from "@features/dashboard/data/useDashboardData";
import { useDashboardActions, useSelectedLaps } from "@features/dashboard/state/useDashboard";
import styles from "./LapSelect.module.css";

// Picks which laps the charts and map show. The selection lives in the URL
// (?laps=): read it with useSelectedLaps; [] means all laps.
export default function LapSelect() {
  const { lapProgress, lapProgressIsLoading, lapProgressError } = useRunLapProgress("overview");
  const selectedLaps = useSelectedLaps();
  const { selectLaps, toggleLap } = useDashboardActions();

  const lapIds = useMemo(() => [...new Set(lapProgress?.lapId)], [lapProgress]);

  const status = lapProgressIsLoading
    ? "Loading laps…"
    : lapProgressError
      ? "Laps unavailable"
      : lapIds.length === 0
        ? "No laps detected"
        : null;
  const label =
    selectedLaps.length === 0
      ? "All laps"
      : `${selectedLaps.length === 1 ? "Lap" : "Laps"} ${selectedLaps.join(", ")}`;

  if (status) return <p className={styles.status}>{status}</p>;

  return (
    <details className={styles.root}>
      <summary className={styles.button}>{label}</summary>
      <fieldset className={styles.menu}>
        <legend className={styles.srOnly}>Laps</legend>
        <label className={styles.option}>
          <input
            type="checkbox"
            checked={selectedLaps.length === 0}
            onChange={() => selectLaps([])}
          />
          All laps
        </label>
        {lapIds.map((lapId) => (
          <label key={lapId} className={styles.option}>
            <input
              type="checkbox"
              checked={selectedLaps.includes(lapId)}
              onChange={() => toggleLap(lapId)}
            />
            Lap {lapId}
          </label>
        ))}
      </fieldset>
    </details>
  );
}
