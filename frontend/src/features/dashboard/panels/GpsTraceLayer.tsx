import { memo, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useSensorTrace } from "@features/dashboard/data/useDashboardData";
import { useShowGpsSubscription } from "@features/dashboard/state/useDashboard";
import { readingsDots, type Track } from "@features/dashboard/utils/trackmap";
import styles from "./TrackMap.module.css";

const GPS_SENSOR = "TPU/GPS/Location";
// Stable, as useSensorTrace asks.
const GPS_SENSORS = [GPS_SENSOR] as const;

// Where status text sits in the drawing, in SVG units (top-left corner).
const STATUS_X = 2;
const STATUS_Y = 3;

const visibility = (show: boolean) => (show ? "visible" : "hidden");

/**
 * The raw GPS readings (TPU/GPS/Location), one dot per reading, drawn over the
 * road in the track map's SVG, in the same projection as the road. Shown and
 * hidden with the GPS switch (GpsToggle).
 *
 * Toggling doesn't re-render anything: the switch's value arrives through a
 * store subscription that sets the group's `visibility` attribute directly. The
 * one exception is the first time it's switched on, which mounts GpsTrace and
 * starts the request: the readings come from Penelope (needs the VPN), so a run
 * where GPS is never shown never asks for them.
 */
export const GpsTraceLayer = memo(function GpsTraceLayer({ track }: { track: Track }) {
  const groupRef = useRef<SVGGElement>(null);
  const [requested, setRequested] = useState(false);

  const isShown = useShowGpsSubscription((show) => {
    groupRef.current?.setAttribute("visibility", visibility(show));
    // Bails out without rendering once it's already true.
    if (show) setRequested(true);
  });

  // Already on when the map mounts (e.g. switched on before the track loaded).
  useLayoutEffect(() => {
    if (isShown()) setRequested(true);
  }, [isShown]);

  // Read at render so a render never undoes the subscription's last write.
  return (
    <g ref={groupRef} className={styles.gps} visibility={visibility(isShown())}>
      {requested && <GpsTrace track={track} />}
    </g>
  );
});

function GpsTrace({ track }: { track: Track }) {
  const { trace, traceIsLoading, traceError } = useSensorTrace(GPS_SENSORS, "overview");
  const series = trace?.series[GPS_SENSOR];

  const d = useMemo(() => (series ? readingsDots(track, series.values) : ""), [track, series]);

  const status = traceError
    ? "GPS unavailable"
    : traceIsLoading
      ? "Loading GPS…"
      : !d
        ? "No GPS readings"
        : null;

  return (
    <>
      {d && <path className={styles.gpsDots} d={d} />}
      {status && (
        <text className={styles.gpsStatus} x={STATUS_X} y={STATUS_Y}>
          {status}
          {traceError && <title>{traceError.message}</title>}
        </text>
      )}
    </>
  );
}
