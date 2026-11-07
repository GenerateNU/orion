import { useEffect, useMemo, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { ProgressRange } from "@features/dashboard/utils/progress";
import styles from "./LapProgressChart.module.css";

const MIN_DRAG_PX = 4;
const LAP_COLORS = 8;
const WHOLE_LAP: ProgressRange = [0, 1];
const linePaths = uPlot.paths.linear?.();

// One lap's readings: values[i] at progress[i] (0 to 1), in time order.
export type LapSeries = {
  lapId: number;
  progress: number[];
  values: number[];
};

export type LapProgressChartProps = {
  laps: LapSeries[];
  height?: number;
  yLabel?: string;
  visibleRange?: ProgressRange | null;
  onCommitRange?: (range: ProgressRange) => void;
  onResetRange?: () => void;
  onHoverProgress?: (progress: number | null) => void;
};

type ChartCallbacks = Pick<
  LapProgressChartProps,
  "onCommitRange" | "onResetRange" | "onHoverProgress"
>;

const cssStyle = (chart: uPlot, name: string) =>
  getComputedStyle(chart.root).getPropertyValue(name).trim();

// Color follows the lap, so a lap keeps its color whichever laps are shown.
const lapColor = (lapId: number) => `--lap-${((lapId - 1) % LAP_COLORS) + 1}`;

const formatTicks = (ticks: number[], increment: number) => {
  const largest = Math.max(...ticks.map(Math.abs));
  const digits = largest > 0 && increment > 0 ? Math.ceil(Math.log10(largest / increment)) + 1 : 1;
  const format = new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumSignificantDigits: Math.min(Math.max(digits, 1), 21),
  });
  return ticks.map((tick) => format.format(tick));
};

const selectionToRange = (chart: uPlot): ProgressRange | null => {
  const { left, width } = chart.select;
  if (width < MIN_DRAG_PX) return null;
  return [chart.posToVal(left, "x"), chart.posToVal(left + width, "x")];
};

const clearSelection = (chart: uPlot) => {
  chart.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false);
};

const applyRange = (chart: uPlot, range: ProgressRange | null) => {
  const [min, max] = range ?? WHOLE_LAP;
  chart.setScale("x", { min, max });
};

// Overlays one line per lap against lap progress, in uPlot's mode 2 so each lap
// keeps its own progress/value arrays.
export const LapProgressChart = ({
  laps,
  height = 600,
  yLabel = "",
  visibleRange = null,
  onCommitRange,
  onResetRange,
  onHoverProgress,
}: LapProgressChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);
  const draggingRef = useRef(false);
  const rangeRef = useRef(visibleRange);

  const callbacksRef = useRef<ChartCallbacks>({});
  useEffect(() => {
    callbacksRef.current = { onCommitRange, onResetRange, onHoverProgress };
  });

  // Mode 2 data is [null, [x, y] per series]; uPlot's AlignedData type only
  // describes mode 1.
  const data = useMemo(
    () => [null, ...laps.map((lap) => [lap.progress, lap.values])] as unknown as uPlot.AlignedData,
    [laps],
  );
  const dataRef = useRef(data);

  const opts = useMemo(
    (): uPlot.Options => ({
      mode: 2,
      width: 0,
      height,
      legend: {
        live: false,
        markers: {
          stroke: (_chart, i) => `var(${lapColor(laps[i - 1].lapId)})`,
          fill: (_chart, i) => `var(${lapColor(laps[i - 1].lapId)})`,
        },
      },
      focus: { alpha: 0.3 },
      scales: {
        x: { time: false, auto: false },
        y: {
          range: (_chart, min, max) => {
            const pad = (max - min) * 0.1 || 1;
            return [min - pad, max + pad];
          },
        },
      },
      axes: [
        {
          label: "Lap progress",
          values: (_chart, ticks) => ticks.map((tick) => `${Math.round(tick * 100)}%`),
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
        focus: { prox: 16 },
      },
      series: [
        {},
        ...laps.map(({ lapId }) => ({
          label: `Lap ${lapId}`,
          stroke: (chart: uPlot) => cssStyle(chart, lapColor(lapId)),
          width: 1.5,
          paths: linePaths,
          points: { show: false },
        })),
      ],
      hooks: {
        setSelect: [
          (chart) => {
            if (draggingRef.current) {
              draggingRef.current = false;
              const selected = selectionToRange(chart);
              if (selected) callbacksRef.current.onCommitRange?.(selected);
            }
            clearSelection(chart);
          },
        ],
        setCursor: [
          (chart) => {
            const { left } = chart.cursor;
            callbacksRef.current.onHoverProgress?.(
              left == null || left < 0 ? null : chart.posToVal(left, "x"),
            );
          },
        ],
      },
    }),
    [height, yLabel, laps],
  );

  useEffect(() => {
    dataRef.current = data;
    const chart = chartRef.current;
    if (!chart || chart.data === data) return;
    chart.setData(data);
    applyRange(chart, rangeRef.current);
  }, [data]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = new uPlot({ ...opts, width: el.clientWidth }, dataRef.current, el);
    chartRef.current = chart;
    applyRange(chart, rangeRef.current);

    const onDown = () => {
      draggingRef.current = true;
    };
    const onUp = () => {
      draggingRef.current = false;
    };
    const onDoubleClick = () => callbacksRef.current.onResetRange?.();

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
    rangeRef.current = visibleRange;
    if (draggingRef.current) return;
    const chart = chartRef.current;
    if (chart) applyRange(chart, visibleRange);
  }, [visibleRange]);

  return <div ref={containerRef} className={styles.chart} />;
};
