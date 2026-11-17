import Switch from "@components/ui/Switch";
import { useDashboardActions, useShowGps } from "@features/dashboard/state/useDashboard";

// Shows or hides the raw GPS readings on the track map (GpsTraceLayer). Only
// this switch re-renders when it's toggled; the map layer listens directly.
export default function GpsToggle() {
  const showGps = useShowGps();
  const { setShowGps } = useDashboardActions();

  return <Switch checked={showGps} onCheckedChange={setShowGps} label="Show GPS data" />;
}
