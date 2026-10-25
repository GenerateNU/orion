import { useEffect, useMemo, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { useVisibleWindow, useDashboardActions } from "@features/dashboard/state/useDashboard";
import type { RunTime, TimeWindow } from "@features/dashboard/utils/time";
import styles from "./TimeSeriesChart.module.css";
import { formatDuration } from "@utils/format";

const MIN_DRAG_PX = 4;

export type ChartSeries = {
  id: string;
  label: string;
  unit: string;
  time: RunTime[];
  values: number[];
};

export type TimeSeriesChartProps = {
  series: ChartSeries[];
  height?: number;
  yLabel?: string;
};

const cssStyle = (chart: uPlot, name: string) =>
  getComputedStyle(chart.root).getPropertyValue(name).trim();

const formatReading = (raw: number | null, unit: string) => {
  if (raw == null) return "";
  return `${raw.toFixed(1)} ${unit}`;
};

const formatTime = (ms: number) => formatDuration(ms / 1000);

const selectionToWindow = (chart: uPlot): TimeWindow | null => {
  const { left, width } = chart.select;
  if (width < MIN_DRAG_PX) return null;
  const start = chart.posToVal(left, "x");
  const end = chart.posToVal(left + width, "x");
  return [start, end];
};

const clearSelection = (chart: uPlot) => {
  chart.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false);
};

const applyWindow = (chart: uPlot, timeWindow: TimeWindow | null) => {
  const times = chart.data[0];
  if (times.length === 0) return;
  const [min, max] = timeWindow ?? [times[0], times[times.length - 1]];
  chart.setScale("x", { min, max });
};

export const TimeSeriesChart = ({ series, height = 600, yLabel = "" }: TimeSeriesChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);
  const draggingRef = useRef(false);

  const visibleWindow = useVisibleWindow();
  const windowRef = useRef(visibleWindow);
  const { previewWindow, commitWindow, resetWindow, setHoverTime } = useDashboardActions();

  const data = useMemo(
    () => uPlot.join(series.map((sensor): uPlot.AlignedData => [sensor.time, sensor.values])),
    [series],
  );

  const opts: uPlot.Options = useMemo(
    () => ({
      width: 0,
      height,
      scales: {
        x: { time: false },
        y: {
          range: (_chart, min, max) => {
            const pad = (max - min) * 0.1 || 1;
            return [min - pad, max + pad];
          },
        },
      },
      axes: [
        {
          label: "Time",
          values: (_chart, ticks) => ticks.map(formatTime),
          stroke: (chart) => cssStyle(chart, "--text-muted"),
          grid: { stroke: (chart) => cssStyle(chart, "--border-default") },
          ticks: { stroke: (chart) => cssStyle(chart, "--border-default") },
        },
        {
          label: yLabel,
          size: 60,
          stroke: (chart) => cssStyle(chart, "--text-muted"),
          grid: { stroke: (chart) => cssStyle(chart, "--border-default") },
          ticks: { stroke: (chart) => cssStyle(chart, "--border-default") },
        },
      ],
      cursor: {
        y: false,
        sync: { key: "dashboard-run" },
        drag: { x: true, y: false, setScale: false },
        bind: { dblclick: () => null },
      },
      series: [
        { label: "Time", value: (_chart, raw) => (raw == null ? "--" : formatTime(raw)) },
        ...series.map(({ label, unit }) => ({
          label,
          stroke: "#d4b06a",
          width: 1.5,
          value: (_self: uPlot, raw: number | null) => formatReading(raw, unit),
        })),
      ],
      hooks: {
        setSelect: [
          (chart) => {
            const selected = selectionToWindow(chart);
            if (selected) commitWindow(selected);
            clearSelection(chart);
          },
        ],
        setCursor: [
          (chart) => {
            const idx = chart.cursor.idx;
            setHoverTime(idx == null ? null : chart.data[0][idx]);
          },
        ],
      },
    }),
    [height, yLabel, series, commitWindow, setHoverTime],
  );

  useEffect(() => {
    const refTag = containerRef.current;
    if (!refTag) return;

    const chart = new uPlot({ ...opts, width: refTag.clientWidth }, data, refTag);
    chartRef.current = chart;
    applyWindow(chart, windowRef.current);

    const onDown = () => {
      draggingRef.current = true;
    };
    const onMove = () => {
      if (!draggingRef.current) return;
      const selected = selectionToWindow(chart);
      if (selected) previewWindow(selected);
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      applyWindow(chart, windowRef.current);
    };
    const onDoubleClick = () => resetWindow();

    chart.over.addEventListener("mousedown", onDown);
    chart.over.addEventListener("mousemove", onMove);
    chart.over.addEventListener("dblclick", onDoubleClick);
    window.addEventListener("mouseup", onUp);

    return () => {
      window.removeEventListener("mouseup", onUp);
      chart.destroy();
      chartRef.current = null;
    };
  }, [opts, data, height, previewWindow, resetWindow]);

  useEffect(() => {
    windowRef.current = visibleWindow;
    if (draggingRef.current) return;
    const chart = chartRef.current;
    if (chart) applyWindow(chart, visibleWindow);
  }, [visibleWindow]);

  return <div ref={containerRef} className={styles.chart} />;
};
