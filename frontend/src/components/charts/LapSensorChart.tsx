import { useMemo } from "react";
import { useLapSensorTraces } from "@features/dashboard/data/useDashboardData";
import { useDashboardActions, usePercentWindow } from "@features/dashboard/state/useDashboard";
import { lapColor } from "@features/dashboard/utils/laps";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import EmptyState from "@components/ui/EmptyState";
import { TimeSeriesChart, type ChartSeries } from "./TimeSeriesChart";
import styles from "./LapSensorChart.module.css";

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
          label: `lap ${trace.lapId}`,
          unit,
          time: trace.percent,
          values: trace.values,
          color: lapColor(trace.lapId),
        })),
    [traces, name, unit],
  );

  if (tracesError) return <ErrorState error={tracesError} />;
  if (tracesIsLoading) return <LoadingState message="Loading sensor data…" />;
  if (series.length === 0) {
    return <EmptyState message="The selected laps have no readings for this sensor." />;
  }

  return (
    <div>
      <TimeSeriesChart
        series={series}
        height={height}
        xAxis="track"
        tooltip
        visibleWindow={percentWindow}
        onCommitWindow={commitPercentWindow}
        onResetWindow={resetPercentWindow}
      />
      {/* Which color is which lap; laps are picked above the track map, not here. */}
      <ul className={styles.legend} aria-label="Laps">
        {series.map(({ id, label, color }) => (
          <li key={id}>
            <span className={styles.dot} style={{ background: color }} aria-hidden="true" />
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
