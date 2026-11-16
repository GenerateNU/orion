import { useEffect, useMemo, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { LapTrace } from "@features/dashboard/utils/laps";
import styles from "./LapPercentChart.module.css";

// One color per lap, cycling after ten; readable on light and dark backgrounds.
const LAP_COLORS = [
  "#3b82f6",
  "#f59e0b",
  "#22c55e",
  "#ef4444",
  "#a855f7",
  "#14b8a6",
  "#ec4899",
  "#84cc16",
  "#f97316",
  "#6366f1",
];

const lapColor = (index: number) => LAP_COLORS[index % LAP_COLORS.length];

const cssStyle = (chart: uPlot, name: string) =>
  getComputedStyle(chart.root).getPropertyValue(name).trim();

type LapPercentChartProps = {
  laps: LapTrace[];
  height?: number;
  yLabel?: string;
};

// A sensor against % of lap: every lap as its own line over 0-100%, so laps can be
// compared at the same place on track. Drag to zoom, double-click to zoom back out.
// Not tied to the dashboard's time window or hover, which are in run time.
export default function LapPercentChart({ laps, height = 240, yLabel = "" }: LapPercentChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Laps share one x axis: join puts each lap's readings at their percentages and
  // leaves gaps (null) where a lap has no reading, which `spanGaps` draws across.
  const data = useMemo(
    () => uPlot.join(laps.map((lap): uPlot.AlignedData => [lap.percent, lap.values])),
    [laps],
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const axis = {
      stroke: (chart: uPlot) => cssStyle(chart, "--text-muted"),
      grid: { stroke: (chart: uPlot) => cssStyle(chart, "--border-default") },
      ticks: { stroke: (chart: uPlot) => cssStyle(chart, "--border-default") },
    };
    const chart = new uPlot(
      {
        width: el.clientWidth,
        height,
        legend: { show: false },
        scales: {
          x: { time: false, range: [0, 100] },
          y: {
            range: (_chart, min, max) => {
              const pad = (max - min) * 0.1 || 1;
              return [min - pad, max + pad];
            },
          },
        },
        axes: [
          { ...axis, label: "% of lap", values: (_chart, ticks) => ticks.map((t) => `${t}%`) },
          { ...axis, label: yLabel, labelGap: 8, size: 60 },
        ],
        cursor: { y: false, drag: { x: true, y: false } },
        series: [
          {},
          ...laps.map((lap, index) => ({
            label: `Lap ${lap.lapId}`,
            stroke: lapColor(index),
            width: 1.5,
            spanGaps: true,
          })),
        ],
      },
      data,
      el,
    );

    const observer = new ResizeObserver(([entry]) => {
      if (entry) chart.setSize({ width: entry.contentRect.width, height });
    });
    observer.observe(el);
    return () => {
      observer.disconnect();
      chart.destroy();
    };
  }, [data, laps, height, yLabel]);

  return (
    <div className={styles.wrapper}>
      <div ref={containerRef} className={styles.chart} />
      <ul className={styles.legend}>
        {laps.map((lap, index) => (
          <li key={lap.lapId} className={styles.legendItem}>
            <span className={styles.swatch} style={{ background: lapColor(index) }} />
            Lap {lap.lapId}
          </li>
        ))}
      </ul>
    </div>
  );
}
