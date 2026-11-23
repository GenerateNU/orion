import { useEffect, useMemo, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { RunTime, TimeWindow } from "@features/dashboard/utils/time";
import { formatDuration } from "@utils/format";
import type { Series } from "./series";
import styles from "./TimeSeriesChart.module.css";

const MIN_DRAG_PX = 4;

// The whole lap when xAxis is "track".
const TRACK_RANGE: TimeWindow = [0, 100];

export type ChartSeries = {
  id: string;
  label: string;
  unit: string;
  // The x of each value: RunTime, or track % (0–100) when xAxis is "track".
  time: RunTime[];
  values: number[];
  // Line color, the --data-series-N slot; 1 by default. Give compared laps different ones.
  series?: Series;
  // A line color that overrides `series` (e.g. a lap's color).
  color?: string;
};

export type TimeSeriesChartProps = {
  series: ChartSeries[];
  height?: number;
  // Figma "Plot Line": "track" plots x as the lap's track percentage (0%–100%).
  xAxis?: "time" | "track";
  // While hovering, a tooltip beside the cursor with every series' value at
  // that x (uPlot's legend, moved to the cursor).
  tooltip?: boolean;
  visibleWindow?: TimeWindow | null;
  onCommitWindow?: (window: TimeWindow) => void;
  onResetWindow?: () => void;
  // The x under the cursor (RunTime, or track %), null when it leaves the chart.
  onHoverTime?: (time: RunTime | null) => void;
};

type ChartCallbacks = Pick<
  TimeSeriesChartProps,
  "onCommitWindow" | "onResetWindow" | "onHoverTime"
>;

const cssStyle = (chart: uPlot, name: string) =>
  getComputedStyle(chart.root).getPropertyValue(name).trim();

const formatX = {
  time: (ms: number) => formatDuration(ms / 1000),
  track: (percent: number) => `${Math.round(percent)}%`,
};

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
  xAxis = "time",
  tooltip = false,
  visibleWindow = null,
  onCommitWindow,
  onResetWindow,
  onHoverTime,
}: TimeSeriesChartProps) => {
  // A track chart always spans 0–100% unless zoomed, wherever the data starts and ends.
  const shownWindow = visibleWindow ?? (xAxis === "track" ? TRACK_RANGE : null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);
  const draggingRef = useRef(false);
  const windowRef = useRef(shownWindow);

  const callbacksRef = useRef<ChartCallbacks>({});
  useEffect(() => {
    callbacksRef.current = { onCommitWindow, onResetWindow, onHoverTime };
  });

  const data = useMemo(
    () => uPlot.join(series.map((sensor): uPlot.AlignedData => [sensor.time, sensor.values])),
    [series],
  );
  const dataRef = useRef(data);

  const opts = useMemo((): uPlot.Options => {
    // Figma "Data/Axis" (400 11px mono); a canvas font can't read the CSS token itself.
    const axisFont = `11px ${getComputedStyle(document.documentElement).getPropertyValue("--font-mono").trim()}`;
    // Series `s`'s line color (1-based, like uPlot's series).
    const lineColor = (chart: uPlot, s: number) => {
      const { color, series: slot = 1 } = series[s - 1] ?? {};
      return color ?? cssStyle(chart, `--data-series-${slot}`);
    };
    return {
      width: 0,
      height,
      legend: {
        show: tooltip,
        live: true,
        // A dot in each series' color (uPlot only colors a marker with a border).
        markers: {
          width: () => 1,
          stroke: lineColor,
          fill: lineColor,
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
      // Figma "Plot Line": horizontal grid lines only, no tick marks.
      axes: [
        {
          values: (_chart, ticks) => ticks.map(formatX[xAxis]),
          // Track ticks every 25% (0, 25, 50…) when there's room, finer when zoomed in.
          ...(xAxis === "track" ? { incrs: [1, 5, 25], space: 100 } : {}),
          font: axisFont,
          stroke: (chart) => cssStyle(chart, "--data-axis"),
          grid: { show: false },
          ticks: { show: false },
        },
        {
          // No label, no space reserved for one: callers show the unit themselves.
          size: 48,
          values: (_chart, ticks, _axisIdx, _space, increment) => formatTicks(ticks, increment),
          font: axisFont,
          stroke: (chart) => cssStyle(chart, "--data-axis"),
          grid: { stroke: (chart) => cssStyle(chart, "--data-grid") },
          ticks: { show: false },
        },
      ],
      cursor: {
        y: false,
        // Time and track charts sync only with their own kind: their x values differ.
        sync: { key: `dashboard-${xAxis}` },
        drag: { x: true, y: false, setScale: false },
        bind: { dblclick: () => null },
      },
      series: [
        {
          label: xAxis === "track" ? "% of lap" : "Time",
          value: (_chart, x) => (x == null ? "" : formatX[xAxis](x)),
        },
        ...series.map(({ label, unit }, i) => ({
          label,
          // The value read off the line at the hovered x (see valueAt), so every
          // series shows one even where its points don't line up with the others'.
          value: (chart: uPlot, _raw: number | null, s: number, idx: number | null) => {
            const value = idx == null ? null : valueAt(chart, s, idx);
            return value == null ? "—" : `${value.toFixed(1)} ${unit}`;
          },
          stroke: (chart: uPlot) => lineColor(chart, i + 1),
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
    };
  }, [height, series, xAxis, tooltip]);

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
    windowRef.current = shownWindow;
    if (draggingRef.current) return;
    const chart = chartRef.current;
    if (chart) applyWindow(chart, shownWindow);
  }, [shownWindow]);

  return <div ref={containerRef} className={styles.chart} />;
};
