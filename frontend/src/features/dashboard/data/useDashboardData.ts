import { useCallback, useMemo } from "react";
import { keepPreviousData } from "@tanstack/react-query";
import type { MetricsResponse } from "@schemas/metrics.schema";
import type { SensorDataResponse, SensorSeries } from "@schemas/sensor.schema";
import type { StateDataResponse } from "@schemas/state.schema";
import { useMetrics } from "@hooks/useMetrics";
import { useSensorData } from "@hooks/useSensors";
import { useStateEstimation } from "@hooks/useStateEstimation";
import { useCommittedWindow, useDashboardRun } from "@features/dashboard/state/useDashboard";
import { lapsFromMetrics, type Lap } from "@features/dashboard/utils/laps";
import { snapWindow, toIsoRange, type TimeWindow } from "@features/dashboard/utils/time";

// The data panels draw, for the opened run. Each hook wraps an API hook from
// hooks/ (one per backend route): windows go out as ISO ranges, and panels asking
// for the same scope share one request and one cache entry.
//
// Trace data is held once, in the query cache. The schemas parse each time axis
// into a Float64Array of epoch ms as the response arrives, and `select` hands
// panels those cached arrays by reference, never a copy, with the run's `startMs`:
//   RunTime of point i = time[i] - startMs
// Apply it where it's needed (axis labels, hover: setHoverTime(epochX - startMs))
// rather than mapping the array.
//
// Panels never pass a window: they pick a DataScope and the hook reads the
// committed window from the URL itself. Time bounds change only through
// useDashboardActions (commitWindow, selectLaps), and a brush drag
// (useVisibleWindow) can't trigger fetches. While a new window loads, the previous
// one's data stays (`isPlaceholderData`).
//
// TODO(backend): /state and /sensors/data don't downsample yet (no `max_points`),
// so a whole-run request returns every row (100 Hz for state). Add max_points
// before panels fetch the overview.

// "overview": the whole run, e.g. under a brush; one cache entry per run.
// "detail":   the committed window; the whole run (same entry) when none is set.
export type DataScope = "overview" | "detail";

// The window a scope fetches. Snapped and clamped here, so a hand-edited URL
// shares cache entries with windows set through commitWindow.
const useFetchWindow = (scope: DataScope): TimeWindow | null => {
  const { timeline } = useDashboardRun();
  const committed = useCommittedWindow();
  const durationMs = timeline?.durationMs;
  return useMemo(() => {
    if (scope === "overview" || !committed) return null;
    return durationMs === undefined ? committed : snapWindow(committed, durationMs);
  }, [scope, committed, durationMs]);
};

export const useLaps = () => {
  const { runId, timeline } = useDashboardRun();
  const select = useCallback(
    (metrics: MetricsResponse): Lap[] => (timeline ? lapsFromMetrics(metrics, timeline) : []),
    [timeline],
  );
  const { metrics, metricsIsLoading, metricsError } = useMetrics(runId, { select, enabled: !!timeline });
  return { laps: metrics, lapsIsLoading: metricsIsLoading, lapsError: metricsError };
};

export type RunPositions = {
  // The run's start in epoch ms: RunTime = time[i] - startMs.
  startMs: number;
  // Epoch ms, ascending. The cached array: read it, don't mutate it.
  time: Float64Array;
  // [latitude, longitude], same length as `time`.
  positions: [number, number][];
};

export const useRunPositions = (scope: DataScope) => {
  const { runId, timeline } = useDashboardRun();
  // Queries only run once the timeline is known, so `select` never sees the 0.
  const startMs = timeline?.startMs ?? 0;
  const window = useFetchWindow(scope);
  const range = useMemo(() => (timeline ? toIsoRange(timeline, window, "naive") : undefined), [timeline, window]);
  const select = useCallback(
    (data: StateDataResponse): RunPositions => ({ startMs, time: data.time, positions: data.positions }),
    [startMs],
  );
  const { stateData, stateDataIsLoading, stateDataIsPlaceholderData, stateDataError } = useStateEstimation(
    runId,
    range,
    { select, placeholderData: keepPreviousData },
  );
  return {
    positions: stateData,
    positionsIsLoading: stateDataIsLoading,
    positionsIsPlaceholderData: stateDataIsPlaceholderData,
    positionsError: stateDataError,
  };
};

export type SensorTraces = {
  // The run's start in epoch ms: RunTime = series[name].time[i] - startMs.
  startMs: number;
  // Keyed by `dataTypeName`. Each series' `time` is epoch ms (the cached
  // Float64Array) and `values[i]` is Penelope's unnamed `values[]` per reading,
  // e.g. [lat, lon] for TPU/GPS/Location.
  series: Record<string, SensorSeries>;
};

// Raw readings straight from Penelope, keyed by `dataTypeName` (list them with
// useSensors). Keep `sensors` stable (a constant or memo). Needs Penelope
// reachable (VPN), unlike the pipeline outputs above.
export const useSensorTrace = (sensors: readonly string[], scope: DataScope) => {
  const { runId, timeline } = useDashboardRun();
  // Queries only run once the timeline is known, so `select` never sees the 0.
  const startMs = timeline?.startMs ?? 0;
  const window = useFetchWindow(scope);
  const range = useMemo(
    () => (timeline ? { sensors: [...sensors].sort(), ...toIsoRange(timeline, window, "utc") } : undefined),
    [timeline, window, sensors],
  );
  const select = useCallback(
    (data: SensorDataResponse): SensorTraces => ({ startMs, series: data.series }),
    [startMs],
  );
  const { sensorData, sensorDataIsLoading, sensorDataIsPlaceholderData, sensorDataError } = useSensorData(
    runId,
    range,
    { select, placeholderData: keepPreviousData },
  );
  return {
    trace: sensorData,
    traceIsLoading: sensorDataIsLoading,
    traceIsPlaceholderData: sensorDataIsPlaceholderData,
    traceError: sensorDataError,
  };
};
