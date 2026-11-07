import { useMemo } from "react";
import { useRunLapProgress, useSensorTrace } from "@features/dashboard/data/useDashboardData";
import { useSelectedLaps } from "@features/dashboard/state/useDashboard";
import { progressAtTimes } from "@features/dashboard/utils/progress";
import type { LapSeries } from "./LapProgressChart";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import EmptyState from "@components/ui/EmptyState";
import DashboardLapProgressChart from "./DashboardLapProgressChart";

type SensorChartProps = {
  name: string;
  unit: string;
  height: number;
};

export default function SensorChart({ name, unit, height }: SensorChartProps) {
  const sensorNames = useMemo(() => [name], [name]);
  const { trace, traceIsLoading, traceIsPlaceholderData, traceError } = useSensorTrace(
    sensorNames,
    "overview",
  );
  const { lapProgress, lapProgressIsLoading, lapProgressError } = useRunLapProgress("overview");
  const selectedLaps = useSelectedLaps();

  // One series per lap, in lap order; only the selected laps when any are selected.
  const laps = useMemo<LapSeries[] | undefined>(() => {
    const sensor = trace?.series[name];
    if (!sensor || !lapProgress) return undefined;
    const matched = progressAtTimes(sensor.time, lapProgress);
    const shown = new Set(selectedLaps);
    const byLap = new Map<number, LapSeries>();
    sensor.time.forEach((_time, i) => {
      const value = sensor.values[i]?.[0];
      const lapId = matched.lapId[i];
      const progress = matched.progress[i];
      if (value == null || lapId == null || progress == null) return;
      if (shown.size > 0 && !shown.has(lapId)) return;
      let lap = byLap.get(lapId);
      if (!lap) {
        lap = { lapId, progress: [], values: [] };
        byLap.set(lapId, lap);
      }
      lap.progress.push(progress);
      lap.values.push(value);
    });
    return byLap.size > 0 ? [...byLap.values()] : undefined;
  }, [trace, lapProgress, name, selectedLaps]);

  const error = traceError ?? lapProgressError;
  if (error) return <ErrorState error={error} />;
  if (traceIsLoading || traceIsPlaceholderData || !trace || lapProgressIsLoading) {
    return <LoadingState message="Loading sensor data…" />;
  }
  if (!laps) return <EmptyState message="This run has no readings for this sensor." />;

  return <DashboardLapProgressChart laps={laps} height={height} yLabel={unit} />;
}
