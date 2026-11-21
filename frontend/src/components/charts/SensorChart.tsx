import { useMemo } from "react";
import { type RunTime } from "@features/dashboard/utils/time";
import { useSensorTrace } from "@features/dashboard/data/useDashboardData";
import type { ChartSeries } from "./TimeSeriesChart";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import EmptyState from "@components/ui/EmptyState";
import TimeSeriesChartFunctionality from "./TimeSeriesChartFunctionality";

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
    // The series can be listed with no readings in it: that's the empty state too.
    if (time.length === 0) return undefined;
    return [{ id: name, label: name, unit, time, values }];
  }, [trace, name, unit]);

  if (traceError) return <ErrorState error={traceError} />;
  if (traceIsLoading || traceIsPlaceholderData || !trace) {
    return <LoadingState message="Loading sensor data…" />;
  }
  if (!series) return <EmptyState message="This run has no readings for this sensor." />;

  // The unit is in the card title, so the axis needs no label.
  return <TimeSeriesChartFunctionality series={series} height={height} />;
}
