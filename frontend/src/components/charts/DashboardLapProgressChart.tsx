import { LapProgressChart, type LapProgressChartProps } from "@components/charts/LapProgressChart";
import {
  useDashboardActions,
  useVisibleProgressRange,
} from "@features/dashboard/state/useDashboard";

type DashboardLapProgressChartProps = Pick<LapProgressChartProps, "laps" | "height" | "yLabel">;

export default function DashboardLapProgressChart(props: DashboardLapProgressChartProps) {
  const visibleRange = useVisibleProgressRange();
  const { commitProgressRange, resetProgressRange, setHoverProgress } = useDashboardActions();

  return (
    <LapProgressChart
      {...props}
      visibleRange={visibleRange}
      onCommitRange={commitProgressRange}
      onResetRange={resetProgressRange}
      onHoverProgress={setHoverProgress}
    />
  );
}
