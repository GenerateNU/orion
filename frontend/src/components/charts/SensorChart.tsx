import { useMemo } from "react";
import { type RunTime } from "@features/dashboard/utils/time";
import { useSensorTrace } from "@features/dashboard/data/useDashboardData";
import { lapTraces } from "@features/dashboard/utils/laps";
import type { ChartSeries } from "./TimeSeriesChart";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import EmptyState from "@components/ui/EmptyState";
import TimeSeriesChartFunctionality from "./TimeSeriesChartFunctionality";
import LapPercentChart from "./LapPercentChart";

// What a sensor chart's x axis shows: run time, or % of lap with one line per lap.
export type XAxis = "time" | "lapPercent";

type SensorChartProps = {
  name: string;
  unit: string;
  height: number;
  xAxis?: XAxis;
};

export default function SensorChart({ name, unit, height, xAxis = "time" }: SensorChartProps) {
  const byLap = xAxis === "lapPercent";
  const sensorNames = useMemo(() => [name], [name]);
  const { trace, traceIsLoading, traceIsPlaceholderData, traceError } = useSensorTrace(
    sensorNames,
    "overview",
    byLap,
  );

  const series = useMemo<ChartSeries[] | undefined>(() => {
    const sensor = trace?.series[name];
    if (!trace || !sensor) return undefined;
    const time: RunTime[] = [];
    const values: number[] = [];
    sensor.time.forEach((t, i) => {
      const value = sensor.values[i]?.[0];
      if (value == null) return;
      time.push((t - trace.startMs) as RunTime);
      values.push(value);
    });
    return [{ id: name, label: name, unit, time, values }];
  }, [trace, name, unit]);

  const laps = useMemo(() => {
    const sensor = trace?.series[name];
    return byLap && sensor ? lapTraces(sensor) : [];
  }, [byLap, trace, name]);

  if (traceError) return <ErrorState error={traceError} />;
  if (traceIsLoading || traceIsPlaceholderData || !trace) {
    return <LoadingState message="Loading sensor data…" />;
  }
  if (!series) return <EmptyState message="This run has no readings for this sensor." />;

  if (byLap) {
    if (laps.length === 0) {
      return (
        <EmptyState message="No lap percentages for this run yet. Run its pipeline to compute them." />
      );
    }
    return <LapPercentChart laps={laps} height={height} yLabel={unit} />;
  }
  return <TimeSeriesChartFunctionality series={series} height={height} yLabel={unit} />;
}
