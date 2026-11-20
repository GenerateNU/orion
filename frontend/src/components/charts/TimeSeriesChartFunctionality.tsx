import { useRef } from "react";
import {
  TimeSeriesChart,
  type TimeSeriesChartHandle,
  type TimeSeriesChartProps,
} from "@components/charts/TimeSeriesChart";
import {
  useDashboardActions,
  useHoverTimeSubscription,
  useVisibleWindow,
} from "@features/dashboard/state/useDashboard";

type DashboardTimeSeriesChartProps = Pick<TimeSeriesChartProps, "series" | "height">;

// A TimeSeriesChart linked to the rest of the dashboard: the committed window is its
// X range, and hover anywhere (charts, track map) moves its cursor.
export default function DashboardTimeSeriesChart(props: DashboardTimeSeriesChartProps) {
  const visibleWindow = useVisibleWindow();
  const { commitWindow, resetWindow, setHoverTime } = useDashboardActions();

  const chartRef = useRef<TimeSeriesChartHandle>(null);
  useHoverTimeSubscription((time) => chartRef.current?.showHoverTime(time));

  return (
    <TimeSeriesChart
      {...props}
      ref={chartRef}
      visibleWindow={visibleWindow}
      onCommitWindow={commitWindow}
      onResetWindow={resetWindow}
      onHoverTime={setHoverTime}
    />
  );
}
