import { useMemo, type ReactNode } from "react";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import { useSensorTrace } from "@features/dashboard/data/useDashboardData";
import { useDashboardActions, useVisibleWindow } from "@features/dashboard/state/useDashboard";
import type { RunTime } from "@features/dashboard/utils/time";
import styles from "./SensorChartPanel.module.css";
import TimeSeriesChartFunctionality from "./TimeSeriesChartFunctionality";

export type PanelSensor = {
  name: string;
  label?: string;
  unit: string;
};

type SensorChartsPanelProps = {
  title: string;
  sensors: readonly PanelSensor[];
  height?: number;
};

export default function SensorChartsPanel({
  title,
  sensors,
  height = 240,
}: SensorChartsPanelProps) {
  const names = useMemo(() => sensors.map((sensor) => sensor.name), [sensors]);
  const { trace, traceIsLoading, traceError } = useSensorTrace(names, "overview");
  const visibleWindow = useVisibleWindow();
  const { resetWindow } = useDashboardActions();

  const charts = useMemo(() => {
    if (!trace) return [];
    return sensors.flatMap(({ name, label, unit }) => {
      const sensor = trace.series[name];
      if (!sensor) return [];
      const time: RunTime[] = [];
      const values: number[] = [];
      sensor.time.forEach((t, i) => {
        const value = sensor.values[i]?.[0];
        if (value == null) return;
        time.push((t - trace.startMs) as RunTime);
        values.push(value);
      });
      return [{ name, unit, series: [{ id: name, label: label ?? name, unit, time, values }] }];
    });
  }, [trace, sensors]);

  let content: ReactNode;
  if (traceIsLoading || (!trace && !traceError))
    content = <LoadingState message="Loading sensor data…" />;
  else if (traceError) content = <ErrorState error={traceError} />;
  else if (charts.length === 0)
    content = <EmptyState message="This run has no readings for these sensors." />;
  else
    content = charts.map((chart) => (
      <div key={chart.name} className={styles.chart}>
        <h4 className={styles.chartTitle}>
          {chart.name} ({chart.unit})
        </h4>
        <TimeSeriesChartFunctionality series={chart.series} height={height} yLabel={chart.unit} />
      </div>
    ));

  return (
    <section className={styles.panel} aria-label={title}>
      <header className={styles.header}>
        <button
          type="button"
          className={styles.reset}
          onClick={() => resetWindow()}
          disabled={visibleWindow === null}
        >
          Reset zoom
        </button>
      </header>
      {content}
    </section>
  );
}
