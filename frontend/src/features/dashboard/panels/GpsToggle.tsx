import Toggle from "@components/ui/Toggle";
import { useDashboardActions, useShowGps } from "@features/dashboard/state/useDashboard";

// Shows or hides the raw GPS readings on the track map (GpsTraceLayer). Only
// this switch re-renders when it's toggled; the map layer listens directly.
export default function GpsToggle() {
  const showGps = useShowGps();
  const { setShowGps } = useDashboardActions();

  return (
    <Toggle
      checked={showGps}
      onChange={(e) => setShowGps(e.target.checked)}
      label="Show GPS data"
    />
  );
}
