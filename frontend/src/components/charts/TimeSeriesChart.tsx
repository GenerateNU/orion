import { useEffect, useImperativeHandle, useMemo, useRef, type Ref } from "react";
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

// Moves the cursor to a time hovered elsewhere (another chart, the track map)
// without re-rendering. Null hides it.
export type TimeSeriesChartHandle = {
  showHoverTime: (time: RunTime | null) => void;
};

export type TimeSeriesChartProps = {
  ref?: Ref<TimeSeriesChartHandle>;
  series: ChartSeries[];
  height?: number;
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
  ref,
  series,
  height = 600,
  visibleWindow = null,
  onCommitWindow,
  onResetWindow,
  onHoverTime,
}: TimeSeriesChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);
  const draggingRef = useRef(false);
  const windowRef = useRef(visibleWindow);

  useImperativeHandle(
    ref,
    () => ({
      showHoverTime: (time) => {
        const chart = chartRef.current;
        // The chart under the pointer already draws its own cursor.
        if (!chart || chart.over.matches(":hover")) return;
        const left = time === null ? -1 : chart.valToPos(time, "x");
        const inside = left >= 0 && left <= chart.over.clientWidth;
        // fireHook false: a cursor moved from outside isn't reported back as hover.
        chart.setCursor({ left: inside ? left : -10, top: chart.cursor.top ?? 0 }, false);
      },
    }),
    [],
  );

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
      legend: { show: false },
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
          values: (_chart, ticks) => ticks.map(formatTime),
          stroke: (chart) => cssStyle(chart, "--text-muted"),
          grid: { stroke: (chart) => cssStyle(chart, "--border-default") },
          ticks: { stroke: (chart) => cssStyle(chart, "--border-default") },
        },
        {
          // No label, no space reserved for one: callers show the unit themselves.
          size: 48,
          values: (_chart, ticks, _axisIdx, _space, increment) => formatTicks(ticks, increment),
          stroke: (chart) => cssStyle(chart, "--text-muted"),
          grid: { stroke: (chart) => cssStyle(chart, "--border-default") },
          ticks: { stroke: (chart) => cssStyle(chart, "--border-default") },
        },
      ],
      cursor: {
        y: false,
        drag: { x: true, y: false, setScale: false },
        bind: { dblclick: () => null },
      },
      series: [
        {},
        ...series.map(({ label }) => ({
          label,
          stroke: "#d4b06a",
          width: 1.5,
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
            const idx = chart.cursor.idx;
            callbacksRef.current.onHoverTime?.(
              idx == null ? null : (chart.data[0][idx] as RunTime),
            );
          },
        ],
      },
    }),
    [height, series],
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
