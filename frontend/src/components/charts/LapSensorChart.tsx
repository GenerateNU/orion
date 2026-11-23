import { useMemo } from "react";
import { useLapSensorTraces } from "@features/dashboard/data/useDashboardData";
import { useDashboardActions, usePercentWindow } from "@features/dashboard/state/useDashboard";
import { lapSeries } from "@features/dashboard/utils/laps";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import EmptyState from "@components/ui/EmptyState";
import { TimeSeriesChart, type ChartSeries } from "./TimeSeriesChart";

type LapSensorChartProps = {
  name: string;
  unit: string;
  height: number;
  lapIds: readonly number[];
};

// One sensor for the selected laps, overlaid by lap percent: one line per lap in
// its lap color. Dragging zooms every chart to the same percent window.
export default function LapSensorChart({ name, unit, height, lapIds }: LapSensorChartProps) {
  const { traces, tracesIsLoading, tracesError } = useLapSensorTraces(name, lapIds);
  const percentWindow = usePercentWindow();
  const { commitPercentWindow, resetPercentWindow } = useDashboardActions();

  const series = useMemo<ChartSeries[]>(
    () =>
      traces
        .filter((trace) => trace.percent.length > 0)
        .map((trace) => ({
          id: `${name}-lap-${trace.lapId}`,
          label: `Lap ${trace.lapId}`,
          unit,
          time: trace.percent,
          values: trace.values,
          series: lapSeries(trace.lapId, lapIds),
        })),
    [traces, name, unit, lapIds],
  );

  if (tracesError) return <ErrorState error={tracesError} />;
  if (tracesIsLoading) return <LoadingState message="Loading sensor data…" />;
  if (series.length === 0) {
    return <EmptyState message="The selected laps have no readings for this sensor." />;
  }

  return (
    <TimeSeriesChart
      series={series}
      height={height}
      xAxis="track"
      tooltip
      visibleWindow={percentWindow}
      onCommitWindow={commitPercentWindow}
      onResetWindow={resetPercentWindow}
    />
  );
}
