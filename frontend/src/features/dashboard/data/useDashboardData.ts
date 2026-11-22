import { useCallback, useMemo } from "react";
import { keepPreviousData } from "@tanstack/react-query";
import type { LapsResponse } from "@schemas/lap.schema";
import type {
  LapSensorDataResponse,
  SensorDataResponse,
  SensorSeries,
} from "@schemas/sensor.schema";
import type { StateDataResponse } from "@schemas/state.schema";
import { useRunLaps } from "@hooks/useRunLaps";
import { useLapSensorData, useSensorData } from "@hooks/useSensors";
import { useStateEstimation } from "@hooks/useStateEstimation";
import {
  useCommittedWindow,
  useDashboardRun,
  useSelectedLaps,
} from "@features/dashboard/state/useDashboard";
import { lapsFromMetrics, MIN_LAPS_TO_COMPARE, type Lap } from "@features/dashboard/utils/laps";
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
    (response: LapsResponse): Lap[] => (timeline ? lapsFromMetrics(response, timeline) : []),
    [timeline],
  );
  const { laps, lapsIsLoading, lapsError } = useRunLaps(runId, { select, enabled: !!timeline });
  return { laps, lapsIsLoading, lapsError };
};

// True when the run has enough laps to compare them by lap percent: the charts
// then plot the selected laps against % of lap instead of time.
export const useCompareLaps = (): boolean => {
  const { laps } = useLaps();
  return (laps?.length ?? 0) >= MIN_LAPS_TO_COMPARE;
};

// True when the run has laps but none is selected: the panels then show
// NO_LAPS_MESSAGE (utils/laps.ts) instead of data.
export const useNoLapsSelected = (): boolean => {
  const { laps } = useLaps();
  const selectedLaps = useSelectedLaps();
  return !!laps?.length && selectedLaps.length === 0;
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
  const range = useMemo(
    () => (timeline ? toIsoRange(timeline, window, "naive") : undefined),
    [timeline, window],
  );
  const select = useCallback(
    (data: StateDataResponse): RunPositions => ({
      startMs,
      time: data.time,
      positions: data.positions,
    }),
    [startMs],
  );
  const { stateData, stateDataIsLoading, stateDataIsPlaceholderData, stateDataError } =
    useStateEstimation(runId, range, { select });
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
    () =>
      timeline
        ? { sensors: [...sensors].sort(), ...toIsoRange(timeline, window, "utc") }
        : undefined,
    [timeline, window, sensors],
  );
  const select = useCallback(
    (data: SensorDataResponse): SensorTraces => ({ startMs, series: data.series }),
    [startMs],
  );
  const { sensorData, sensorDataIsLoading, sensorDataIsPlaceholderData, sensorDataError } =
    useSensorData(runId, range, { select, placeholderData: keepPreviousData });
  return {
    trace: sensorData,
    traceIsLoading: sensorDataIsLoading,
    traceIsPlaceholderData: sensorDataIsPlaceholderData,
    traceError: sensorDataError,
  };
};

// One lap's readings of a sensor by lap percent: `values[i]` at `percent[i]`,
// ascending, readings with no percent (off track) left out.
export type LapTrace = {
  lapId: number;
  percent: number[];
  values: number[];
};

// Each of `lapIds`' readings of `sensor` (its first value) by lap percent, for
// comparing laps. Keep `lapIds` stable (a memo or the URL's list).
export const useLapSensorTraces = (sensor: string, lapIds: readonly number[]) => {
  const { runId } = useDashboardRun();
  const range = useMemo(() => ({ sensors: [sensor], lap_ids: [...lapIds] }), [sensor, lapIds]);
  const select = useCallback(
    (data: LapSensorDataResponse): LapTrace[] =>
      data.flatMap((response, i): LapTrace[] => {
        const series = response.series[sensor];
        if (!series?.lap_percent) return [];
        const points = series.values
          .map((value, j) => [series.lap_percent?.[j], value[0]] as const)
          .filter(
            (point): point is readonly [number, number] => point[0] != null && point[1] != null,
          )
          .sort((a, b) => a[0] - b[0]);
        return [
          { lapId: lapIds[i], percent: points.map((p) => p[0]), values: points.map((p) => p[1]) },
        ];
      }),
    [sensor, lapIds],
  );
  const { lapSensorData, lapSensorDataIsLoading, lapSensorDataError } = useLapSensorData(
    runId,
    range,
    { select },
  );
  return {
    traces: lapSensorData ?? [],
    tracesIsLoading: lapSensorDataIsLoading,
    tracesError: lapSensorDataError,
  };
};
