import { useId, useMemo, useState } from "react";
import ErrorState from "@components/ui/ErrorState";
import EmptyState from "@components/ui/EmptyState";
import LoadingState from "@components/ui/LoadingState";
import type { ChartSeries } from "@components/charts/TimeSeriesChart";
import { useSensorTrace } from "@features/dashboard/data/useDashboardData";
import { useSensors } from "@hooks/useSensors";
import { useDashboardActions, useVisibleWindow } from "@features/dashboard/state/useDashboard";
import type { RunTime } from "@features/dashboard/utils/time";
import styles from "./SensorChartPanel.module.css";
import TimeSeriesChartFunctionality from "./TimeSeriesChartFunctionality";

const MAX_NUM_CHARTS = 6;

type SensorChartsPanelProps = {
  defaultSensors?: readonly string[];
  height?: number;
};

export default function SensorChartsPanel({
  defaultSensors = [],
  height = 240,
}: SensorChartsPanelProps) {
  const [selected, setSelected] = useState<readonly string[]>(defaultSensors);
  const [adding, setAdding] = useState(false);

  const { sensors } = useSensors();
  const visibleWindow = useVisibleWindow();
  const { resetWindow } = useDashboardActions();

  const units = useMemo(
    () => new Map(sensors?.map((sensor) => [sensor.name, sensor.unit ?? ""])),
    [sensors],
  );
  const available = (sensors ?? [])
    .map((sensor) => sensor.name)
    .filter((name) => name.trim() !== "" && !selected.includes(name));

  return (
    <section className={styles.panel}>
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

      <div className={styles.grid}>
        {selected.map((name, index) => (
          <div key={name} className={styles.chart}>
            <div className={styles.chartHeader}>
              <SensorPicker
                value={name}
                options={available}
                label="Sensor"
                onPick={(next) =>
                  setSelected((prev) => prev.map((n, i) => (i === index ? next : n)))
                }
              />
              <button
                type="button"
                className={styles.remove}
                onClick={() => setSelected((prev) => prev.filter((n) => n !== name))}
              >
                ×
              </button>
            </div>
            <SensorChart name={name} unit={units.get(name) ?? ""} height={height} />
          </div>
        ))}

        {selected.length < MAX_NUM_CHARTS && (
          <div className={styles.addSlot} style={{ minHeight: height }}>
            {adding ? (
              <SensorPicker
                options={available}
                label="Select a sensor to view"
                autoFocus
                onPick={(name) => {
                  setSelected((prev) => [...prev, name]);
                  setAdding(false);
                }}
                onCancel={() => setAdding(false)}
              />
            ) : (
              <button
                type="button"
                className={styles.add}
                onClick={() => setAdding(true)}
                disabled={!sensors}
              >
                +
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

type SensorChartProps = {
  name: string;
  unit: string;
  height: number;
};

function SensorChart({ name, unit, height }: SensorChartProps) {
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
    return [{ id: name, label: name, unit, time, values }];
  }, [trace, name, unit]);

  if (traceError) return <ErrorState error={traceError} />;
  if (traceIsLoading || traceIsPlaceholderData || !trace) {
    return <LoadingState message="Loading sensor data…" />;
  }
  if (!series) return <EmptyState message="This run has no readings for this sensor." />;

  return <TimeSeriesChartFunctionality series={series} height={height} yLabel={unit} />;
}

type SensorPickerProps = {
  value?: string;
  options: readonly string[];
  label: string;
  autoFocus?: boolean;
  onPick: (name: string) => void;
  onCancel?: () => void;
};

function SensorPicker({
  value = "",
  options,
  label,
  autoFocus,
  onPick,
  onCancel,
}: SensorPickerProps) {
  const listId = useId();
  const [text, setText] = useState(value);

  return (
    <>
      <input
        className={styles.picker}
        list={listId}
        value={text}
        placeholder={value || label}
        autoFocus={autoFocus}
        onFocus={() => setText("")}
        onChange={(e) => {
          if (options.includes(e.target.value)) onPick(e.target.value);
          else setText(e.target.value);
        }}
        onBlur={() => {
          setText(value);
          onCancel?.();
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") e.currentTarget.blur();
        }}
      />
      <datalist id={listId}>
        {options.map((name) => (
          <option key={name} value={name} />
        ))}
      </datalist>
    </>
  );
}
