import { useEffect, useMemo, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { RunTime, TimeWindow } from "@features/dashboard/utils/time";
import { formatDuration } from "@utils/format";
import styles from "./TimeSeriesChart.module.css";
 
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
  visibleWindow?: TimeWindow | null;
  onPreviewWindow?: (window: TimeWindow) => void;
  onCommitWindow?: (window: TimeWindow) => void;
  onResetWindow?: () => void;
  onHoverTime?: (time: RunTime | null) => void;
};
 
type ChartCallbacks = Pick<TimeSeriesChartProps, "onPreviewWindow" | "onCommitWindow" | "onResetWindow" | "onHoverTime">;
 
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
 
export const TimeSeriesChart = ({
  series,
  height = 600,
  yLabel = "",
  visibleWindow = null,
  onPreviewWindow,
  onCommitWindow,
  onResetWindow,
  onHoverTime,
}: TimeSeriesChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);
  const draggingRef = useRef(false);
  const windowRef = useRef(visibleWindow);

  const callbacksRef = useRef<ChartCallbacks>({});
  useEffect(() => {
    callbacksRef.current = { onPreviewWindow, onCommitWindow, onResetWindow, onHoverTime };
  });
 
  const data = useMemo(
    () => uPlot.join(series.map((sensor): uPlot.AlignedData => [sensor.time, sensor.values])),
    [series],
  );
  const dataRef = useRef(data);
 
  const opts = useMemo(
    (): uPlot.Options => ({
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
          labelGap: 8,
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
          value: (_chart: uPlot, raw: number | null) => formatReading(raw, unit),
        })),
      ],
      hooks: {
        setSelect: [
          (chart) => {
            const selected = selectionToWindow(chart);
            if (selected) callbacksRef.current.onCommitWindow?.(selected);
            clearSelection(chart);
          },
        ],
        setCursor: [
          (chart) => {
            const idx = chart.cursor.idx;
            callbacksRef.current.onHoverTime?.(idx == null ? null : (chart.data[0][idx] as RunTime));
          },
        ],
      },
    }),
    [height, yLabel, series],
  );
 
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
 
    const chart = new uPlot({ ...opts, width: el.clientWidth }, dataRef.current, el);
    chartRef.current = chart;
    applyWindow(chart, windowRef.current);
 
    const onDown = () => {
      draggingRef.current = true;
    };
    const onMove = () => {
      if (!draggingRef.current) return;
      const selected = selectionToWindow(chart);
      if (selected) callbacksRef.current.onPreviewWindow?.(selected);
    };
    const onUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      applyWindow(chart, windowRef.current);
    };
    const onDoubleClick = () => callbacksRef.current.onResetWindow?.();
 
    chart.over.addEventListener("mousedown", onDown);
    chart.over.addEventListener("mousemove", onMove);
    chart.over.addEventListener("dblclick", onDoubleClick);
    window.addEventListener("mouseup", onUp);
 
    const observer = new ResizeObserver(([entry]) => {
      if (entry) chart.setSize({ width: entry.contentRect.width, height });
    });
    observer.observe(el);
 
    return () => {
      observer.disconnect();
      window.removeEventListener("mouseup", onUp);
      chart.destroy(); 
      chartRef.current = null;
    };
  }, [opts, height]);
 
  useEffect(() => {
    dataRef.current = data;
    const chart = chartRef.current;
    if (!chart || chart.data === data) return;
    chart.setData(data);
    applyWindow(chart, windowRef.current);
  }, [data]);
 
  useEffect(() => {
    windowRef.current = visibleWindow;
    if (draggingRef.current) return;
    const chart = chartRef.current;
    if (chart) applyWindow(chart, visibleWindow);
  }, [visibleWindow]);
 
  return <div ref={containerRef} className={styles.chart} />;
};