import { TimeSeriesChart, type TimeSeriesChartProps } from "@components/charts/TimeSeriesChart";
import { useDashboardActions, useVisibleWindow } from "@features/dashboard/state/useDashboard";

type DashboardTimeSeriesChartProps = Pick<TimeSeriesChartProps, "series" | "height" | "yLabel">;

export default function DashboardTimeSeriesChart(props: DashboardTimeSeriesChartProps) {
  const visibleWindow = useVisibleWindow();
  const { previewWindow, commitWindow, resetWindow, setHoverTime } = useDashboardActions();

  return (
    <TimeSeriesChart
      {...props}
      visibleWindow={visibleWindow}
      onPreviewWindow={previewWindow}
      onCommitWindow={commitWindow}
      onResetWindow={resetWindow}
      onHoverTime={setHoverTime}
    />
  );
}
