import { TimeSeriesChart, type TimeSeriesChartProps } from "@components/charts/TimeSeriesChart";
import { useLaps } from "@features/dashboard/data/useDashboardData";
import {
  useDashboardActions,
  useHoverLap,
  useVisibleWindow,
} from "@features/dashboard/state/useDashboard";

type DashboardTimeSeriesChartProps = Pick<TimeSeriesChartProps, "series" | "height" | "yLabel">;

export default function DashboardTimeSeriesChart(props: DashboardTimeSeriesChartProps) {
  const visibleWindow = useVisibleWindow();
  const { previewWindow, commitWindow, resetWindow, setHoverTime } = useDashboardActions();

  // Shade the lap hovered in the lap list.
  const hoverLap = useHoverLap();
  const { laps } = useLaps();
  const highlightWindow = laps?.find((lap) => lap.id === hoverLap)?.window ?? null;

  return (
    <TimeSeriesChart
      {...props}
      visibleWindow={visibleWindow}
      highlightWindow={highlightWindow}
      onPreviewWindow={previewWindow}
      onCommitWindow={commitWindow}
      onResetWindow={resetWindow}
      onHoverTime={setHoverTime}
    />
  );
}
