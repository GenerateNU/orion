import { useEffect, useMemo, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { RunTime, TimeWindow } from "@features/dashboard/utils/time";
import { formatDuration } from "@utils/format";
import styles from "./TimeSeriesChart.module.css";

const MIN_DRAG_PX = 4;
// A series' line color when it doesn't set one.
const DEFAULT_COLOR = "#d4b06a";

// `time` is the x value of each point: RunTime, or lap percent when comparing laps.
export type ChartSeries = {
  id: string;
  label: string;
  unit: string;
  time: RunTime[];
  values: number[];
  color?: string;
};

export type TimeSeriesChartProps = {
  series: ChartSeries[];
  height?: number;
  yLabel?: string;
  xLabel?: string;
  formatX?: (value: number) => string;
  // While hovering, a tooltip beside the cursor with every series' value at
  // that x (uPlot's legend, moved to the cursor).
  tooltip?: boolean;
  visibleWindow?: TimeWindow | null;
  onCommitWindow?: (window: TimeWindow) => void;
  onResetWindow?: () => void;
  onHoverTime?: (time: RunTime | null) => void;
};

type ChartCallbacks = Pick<
  TimeSeriesChartProps,
  "onCommitWindow" | "onResetWindow" | "onHoverTime"
>;

const cssStyle = (chart: uPlot, name: string) =>
  getComputedStyle(chart.root).getPropertyValue(name).trim();

const formatTime = (ms: number) => formatDuration(ms / 1000);

const formatTicks = (ticks: number[], increment: number) => {
  const largest = Math.max(...ticks.map(Math.abs));
  const digits = largest > 0 && increment > 0 ? Math.ceil(Math.log10(largest / increment)) + 1 : 1;
  const format = new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumSignificantDigits: Math.min(Math.max(digits, 1), 21),
  });
  return ticks.map((tick) => format.format(tick));
};

const selectionToWindow = (chart: uPlot): TimeWindow | null => {
  const { left, width } = chart.select;
  if (width < MIN_DRAG_PX) return null;
  const start = chart.posToVal(left, "x");
  const end = chart.posToVal(left + width, "x");
  return [start, end];
};

// Series `s`'s value at the hovered x, read off its line: interpolated between
// its nearest points either side, since joined series rarely share x values.
// Null outside the series' range.
const valueAt = (chart: uPlot, s: number, idx: number): number | null => {
  const xs = chart.data[0];
  const ys = chart.data[s];
  if (ys[idx] != null) return ys[idx];
  let before = idx - 1;
  while (before >= 0 && ys[before] == null) before--;
  let after = idx + 1;
  while (after < xs.length && ys[after] == null) after++;
  if (before < 0 || after >= xs.length) return null;
  const y0 = ys[before] as number;
  const y1 = ys[after] as number;
  return y0 + ((y1 - y0) * (xs[idx] - xs[before])) / (xs[after] - xs[before]);
};

// Moves uPlot's legend beside the cursor as a tooltip (flipped to its left past
// the middle of the plot), or hides it when the cursor is off the plot.
const placeTooltip = (chart: uPlot) => {
  const el = chart.root.querySelector<HTMLElement>(".u-legend");
  if (!el) return;
  const { idx, left = -1, top = -1 } = chart.cursor;
  el.style.visibility = idx == null || left < 0 ? "hidden" : "visible";
  if (idx == null || left < 0) return;
  const flip = left > chart.over.clientWidth / 2;
  el.style.left = `${chart.over.offsetLeft + left + (flip ? -el.offsetWidth - 12 : 12)}px`;
  el.style.top = `${chart.over.offsetTop + Math.max(0, top - el.offsetHeight / 2)}px`;
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
  xLabel = "Time",
  formatX = formatTime,
  tooltip = false,
  visibleWindow = null,
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
    callbacksRef.current = { onCommitWindow, onResetWindow, onHoverTime };
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
      legend: {
        show: tooltip,
        live: true,
        // A dot in each series' color (uPlot only colors a marker with a border).
        markers: {
          width: () => 1,
          stroke: (_chart, s) => series[s - 1]?.color ?? DEFAULT_COLOR,
          fill: (_chart, s) => series[s - 1]?.color ?? DEFAULT_COLOR,
        },
      },
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
          label: xLabel,
          values: (_chart, ticks) => ticks.map(formatX),
          stroke: (chart) => cssStyle(chart, "--text-muted"),
          grid: { stroke: (chart) => cssStyle(chart, "--border-default") },
          ticks: { stroke: (chart) => cssStyle(chart, "--border-default") },
        },
        {
          label: yLabel,
          labelGap: 8,
          size: 60,
          values: (_chart, ticks, _axisIdx, _space, increment) => formatTicks(ticks, increment),
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
        { label: xLabel, value: (_chart, x) => (x == null ? "" : formatX(x)) },
        ...series.map(({ label, color, unit }) => ({
          label,
          // The value read off the line at the hovered x (see valueAt), so every
          // series shows one even where its points don't line up with the others'.
          value: (chart: uPlot, _raw: number | null, s: number, idx: number | null) => {
            const value = idx == null ? null : valueAt(chart, s, idx);
            return value == null ? "—" : `${value.toFixed(1)} ${unit}`;
          },
          stroke: color ?? DEFAULT_COLOR,
          width: 1.5,
          // Joined series leave gaps at each other's x values; draw through them.
          spanGaps: true,
        })),
      ],
      hooks: {
        setSelect: [
          (chart) => {
            if (draggingRef.current) {
              draggingRef.current = false;
              const selected = selectionToWindow(chart);
              if (selected) callbacksRef.current.onCommitWindow?.(selected);
            }
            clearSelection(chart);
          },
        ],
        setCursor: [
          (chart) => {
            if (tooltip) placeTooltip(chart);
            const idx = chart.cursor.idx;
            callbacksRef.current.onHoverTime?.(
              idx == null ? null : (chart.data[0][idx] as RunTime),
            );
          },
        ],
      },
    }),
    [height, yLabel, xLabel, formatX, tooltip, series],
  );

  useEffect(() => {
    dataRef.current = data;
    const chart = chartRef.current;
    if (!chart || chart.data === data) return;
    chart.setData(data);
    applyWindow(chart, windowRef.current);
  }, [data]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = new uPlot({ ...opts, width: el.clientWidth }, dataRef.current, el);
    chartRef.current = chart;
    applyWindow(chart, windowRef.current);

    const onDown = () => {
      draggingRef.current = true;
    };
    const onUp = () => {
      draggingRef.current = false;
    };
    const onDoubleClick = () => callbacksRef.current.onResetWindow?.();

    chart.over.addEventListener("mousedown", onDown);
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
    windowRef.current = visibleWindow;
    if (draggingRef.current) return;
    const chart = chartRef.current;
    if (chart) applyWindow(chart, visibleWindow);
  }, [visibleWindow]);

  return <div ref={containerRef} className={styles.chart} />;
};
