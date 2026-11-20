import { useId, useMemo, useState } from "react";
import { Plus, X } from "lucide-react";
import Button from "@components/ui/Button";
import IconButton from "@components/ui/IconButton";
import Input from "@components/ui/Input";
import { useSensors } from "@hooks/useSensors";
import { useDashboardActions, useVisibleWindow } from "@features/dashboard/state/useDashboard";
import styles from "./SensorChartPanel.module.css";
import SensorChart from "./SensorChart";

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
        <Button
          variant="secondary"
          size="sm"
          onClick={() => resetWindow()}
          disabled={visibleWindow === null}
        >
          Reset zoom
        </Button>
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
              <IconButton
                label={`Remove ${name} chart`}
                onClick={() => setSelected((prev) => prev.filter((n) => n !== name))}
              >
                <X />
              </IconButton>
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
              <IconButton
                variant="secondary"
                label="Add a chart"
                onClick={() => setAdding(true)}
                disabled={!sensors}
              >
                <Plus />
              </IconButton>
            )}
          </div>
        )}
      </div>
    </section>
  );
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
      <Input
        className={styles.picker}
        aria-label={label}
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
