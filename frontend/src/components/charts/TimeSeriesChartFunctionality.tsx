import { useRef } from "react";
import {
  TimeSeriesChart,
  type TimeSeriesChartHandle,
  type TimeSeriesChartProps,
} from "@components/charts/TimeSeriesChart";
import { useLaps } from "@features/dashboard/data/useDashboardData";
import {
  useDashboardActions,
  useHoverLap,
  useHoverTimeSubscription,
  useVisibleWindow,
} from "@features/dashboard/state/useDashboard";

type DashboardTimeSeriesChartProps = Pick<TimeSeriesChartProps, "series" | "height" | "yLabel">;

// A TimeSeriesChart linked to the rest of the dashboard: the committed window is its
// X range, hover anywhere (charts, track map) moves its cursor, and the hovered lap
// is shaded.
export default function DashboardTimeSeriesChart(props: DashboardTimeSeriesChartProps) {
  const visibleWindow = useVisibleWindow();
  const { commitWindow, resetWindow, setHoverTime } = useDashboardActions();

  const chartRef = useRef<TimeSeriesChartHandle>(null);
  useHoverTimeSubscription((time) => chartRef.current?.showHoverTime(time));

  const hoverLap = useHoverLap();
  const { laps } = useLaps();
  const shadeWindow = laps?.find((lap) => lap.id === hoverLap)?.window ?? null;

  return (
    <TimeSeriesChart
      {...props}
      ref={chartRef}
      visibleWindow={visibleWindow}
      shadeWindow={shadeWindow}
      onCommitWindow={commitWindow}
      onResetWindow={resetWindow}
      onHoverTime={setHoverTime}
    />
  );
}
