import { useEffect, useMemo, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getRouteApi } from "@tanstack/react-router";
import { useStore } from "zustand";
import type { MetricsResponse } from "@schemas/metrics.schema";
import type { RunResponse } from "@schemas/run.schema";
import { runDataKeys, runKeys } from "@api/queryKeys";
import { useRun } from "@hooks/useRuns";
import { useDashboardStoreApi } from "@features/dashboard/state/dashboardStore";
import { lapsFromMetrics, lapsToWindow } from "@features/dashboard/utils/laps";
import type { DashboardSearch } from "@features/dashboard/utils/search";
import {
  runTimeline,
  snapWindow,
  type RunTime,
  type TimeWindow,
} from "@features/dashboard/utils/time";

// The dashboard's state API. Panels read and change shared state only through
// these hooks, so a field can move between the URL and the store without
// touching any panel:
//   URL search params  laps, committed window  (durable, shareable, back/forward)
//   dashboardStore     hover, draft window     (transient, up to once a frame)

const dashboardRoute = getRouteApi("/runs/$runId/dashboard");

const NO_LAPS: readonly number[] = [];

// The opened run and its timeline (the reference for every RunTime).
export const useDashboardRun = () => {
  const { runId } = dashboardRoute.useParams();
  const { run, runIsLoading, runError } = useRun(runId);
  const timeline = useMemo(() => (run ? runTimeline(run) : null), [run]);
  return { runId, run, timeline, runIsLoading, runError };
};

export const useSelectedLaps = (): readonly number[] =>
  dashboardRoute.useSearch({ select: (search) => search.laps ?? NO_LAPS });

// The window set by commitWindow / selectLaps; null is the whole run. The data
// hooks fetch it themselves (data/useDashboardData.ts, scope "detail").
export const useCommittedWindow = (): TimeWindow | null =>
  dashboardRoute.useSearch({ select: (search) => search.t ?? null });

// The window to draw: the brush being dragged if any, else the committed one.
// For drawing and zooming only: draw it from data already loaded. Nothing takes
// it to fetch, so a drag never sends requests; commitWindow on release does.
export const useVisibleWindow = (): TimeWindow | null => {
  const draft = useStore(useDashboardStoreApi(), (state) => state.draftWindow);
  const committed = useCommittedWindow();
  return draft ?? committed;
};

// For React-rendered highlights (lap list rows). Fast-moving hover time has no
// hook like this on purpose: use useHoverTimeSubscription.
export const useHoverLap = (): number | null =>
  useStore(useDashboardStoreApi(), (state) => state.hoverLap);

// Calls `onChange` whenever the hovered run time changes, outside React rendering,
// so charts and the map can move a crosshair or marker imperatively without
// re-rendering on every pointer move.
export const useHoverTimeSubscription = (onChange: (time: RunTime | null) => void) => {
  const store = useDashboardStoreApi();
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  });
  useEffect(
    () =>
      store.subscribe((state, previous) => {
        if (state.hoverTime !== previous.hoverTime) onChangeRef.current(state.hoverTime);
      }),
    [store],
  );
};

// Stable callbacks that change the shared state. They read run and lap data from
// the query cache when called, so using them doesn't subscribe a panel to it.
export const useDashboardActions = () => {
  const { runId } = dashboardRoute.useParams();
  const navigate = dashboardRoute.useNavigate();
  const store = useDashboardStoreApi();
  const queryClient = useQueryClient();

  return useMemo(() => {
    const timeline = () => {
      const run = queryClient.getQueryData<RunResponse>(runKeys.detail(runId));
      return run ? runTimeline(run) : null;
    };

    // The span of the laps; the current window when lap times aren't loaded.
    const windowForLaps = (lapIds: readonly number[], current: TimeWindow | undefined) => {
      if (lapIds.length === 0) return undefined;
      const metrics = queryClient.getQueryData<MetricsResponse>(runDataKeys.metrics(runId));
      const runTimes = timeline();
      if (!metrics || !runTimes) return current;
      return lapsToWindow(lapsFromMetrics(metrics, runTimes), lapIds) ?? current;
    };

    // Lap changes add a history entry, so Back undoes them.
    const setLaps = (update: (laps: readonly number[]) => readonly number[]) => {
      store.getState().setDraftWindow(null);
      navigate({
        search: (prev: DashboardSearch): DashboardSearch => {
          const laps = [...new Set(update(prev.laps ?? NO_LAPS))].sort((a, b) => a - b);
          return {
            ...prev,
            laps: laps.length > 0 ? laps : undefined,
            t: windowForLaps(laps, prev.t),
          };
        },
      });
    };

    // Window changes replace the history entry, so a drag doesn't fill history.
    const setWindow = (window: TimeWindow | null) => {
      store.getState().setDraftWindow(null);
      const runTimes = timeline();
      const t = window && runTimes ? snapWindow(window, runTimes.durationMs) : window;
      navigate({
        search: (prev: DashboardSearch): DashboardSearch => ({ ...prev, t: t ?? undefined }),
        replace: true,
      });
    };

    return {
      // Selecting laps also zooms to their span; an empty list shows the whole run.
      selectLaps: (lapIds: readonly number[]) => setLaps(() => lapIds),
      toggleLap: (lapId: number) =>
        setLaps((laps) =>
          laps.includes(lapId) ? laps.filter((id) => id !== lapId) : [...laps, lapId],
        ),
      // While a brush is dragged: panels redraw from loaded data, nothing is fetched.
      previewWindow: (window: TimeWindow) => store.getState().setDraftWindow(window),
      // On release: snapped, written to the URL, and the detail data fetched.
      commitWindow: (window: TimeWindow) => setWindow(window),
      resetWindow: () => setWindow(null),
      setHoverTime: (time: RunTime | null) => store.getState().setHoverTime(time),
      setHoverLap: (lap: number | null) => store.getState().setHoverLap(lap),
    };
  }, [runId, navigate, store, queryClient]);
};
