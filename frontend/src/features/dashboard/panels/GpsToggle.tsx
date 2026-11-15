import { useDashboardActions, useShowGps } from "@features/dashboard/state/useDashboard";
import styles from "./GpsToggle.module.css";

// Shows or hides the raw GPS readings on the track map (GpsTraceLayer). Only
// this switch re-renders when it's toggled; the map layer listens directly.
export default function GpsToggle() {
  const showGps = useShowGps();
  const { setShowGps } = useDashboardActions();

  return (
    <label className={styles.toggle}>
      <input
        type="checkbox"
        role="switch"
        className={styles.input}
        checked={showGps}
        onChange={(e) => setShowGps(e.target.checked)}
      />
      <span className={styles.track} aria-hidden="true">
        <span className={styles.thumb} />
      </span>
      Show GPS data
    </label>
  );
}
