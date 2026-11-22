import { useCallback, useMemo, useRef, useState, type CSSProperties } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import MonthCalendar from "@components/calendar/MonthCalendar";
import ResizeHandle from "@components/layout/ResizeHandle";
import TopBar from "@components/layout/TopBar";
import DayRunsPanel from "@components/runs/DayRunsPanel";
import RunSearch from "@components/runs/RunSearch";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import Notice from "@components/ui/Notice";
import { usePipelineMutations } from "@hooks/usePipelineRuns";
import { useRunRows } from "@hooks/useRunRows";
import {
  addMonths,
  groupRunsByDay,
  monthOfDay,
  runDayKey,
  toDayKey,
  toMonthKey,
  type DayKey,
} from "@utils/calendar";
import { describeError } from "@utils/describeError";
import type { RunRow } from "@utils/runRows";
import type { RunsSearch } from "@utils/runsSearchParams";
import styles from "./RunsView.module.css";

const NO_RUNS: readonly RunRow[] = [];

// The day panel's width once the user has dragged it; the default is a third of the
// page (RunsView.module.css). Remembered per browser.
const PANEL_WIDTH_KEY = "orion.runs.panelWidth";
const PANEL_MIN_WIDTH = 360;
// Width the calendar always keeps beside the panel (the 504px in the CSS is this
// plus the handle).
const CALENDAR_MIN_WIDTH = 480;
const HANDLE_WIDTH = 24;

function readPanelWidth(): number | null {
  try {
    const value = Number(localStorage.getItem(PANEL_WIDTH_KEY));
    return value >= PANEL_MIN_WIDTH ? value : null;
  } catch {
    return null;
  }
}

function storePanelWidth(width: number | null) {
  try {
    if (width === null) localStorage.removeItem(PANEL_WIDTH_KEY);
    else localStorage.setItem(PANEL_WIDTH_KEY, String(Math.round(width)));
  } catch {
    // Storage blocked (private window…): the width just isn't remembered.
  }
}

// Figma "Runs · Calendar": every run on a month calendar. Clicking a day opens its
// runs in a side panel; a selected run opens its dashboard. The month, day and run
// live in the URL (utils/runsSearchParams.ts) so Back from a dashboard returns here.
export default function RunsView() {
  const search = useSearch({ from: "/runs" });
  const navigate = useNavigate({ from: "/runs" });
  const {
    runRows,
    runRowsIsLoading,
    runRowsError,
    penelopeRunsError,
    runsError,
    pipelineRunsError,
  } = useRunRows();
  const { triggerPipeline, triggerPipelineError } = usePipelineMutations();

  const runsByDay = useMemo(() => groupRunsByDay(runRows), [runRows]);
  const undatedCount = useMemo(() => runRows.filter((row) => !runDayKey(row)).length, [runRows]);

  const today = toDayKey(new Date());
  const selectedDay = search.day ?? null;
  const month = search.month ?? (selectedDay ? monthOfDay(selectedDay) : toMonthKey(new Date()));
  const dayRuns = (selectedDay && runsByDay.get(selectedDay)) || NO_RUNS;

  // In-page selection replaces the history entry; opening a dashboard pushes one.
  const setSearch = useCallback(
    (next: RunsSearch) => navigate({ search: next, replace: true }),
    [navigate],
  );

  const handleSelectDay = useCallback(
    (day: DayKey) => {
      if (day === selectedDay) {
        setSearch({ month });
        return;
      }
      // A lone run is selected straight away; with several the user picks one.
      const runs = runsByDay.get(day) ?? [];
      setSearch({
        month: monthOfDay(day),
        day,
        run: runs.length === 1 ? runs[0].runId : undefined,
      });
    },
    [month, runsByDay, selectedDay, setSearch],
  );

  const handleSelectRun = useCallback(
    (runId: string) => setSearch({ ...search, run: runId }),
    [search, setSearch],
  );

  const handleSearchSelect = useCallback(
    (row: RunRow) => {
      const day = runDayKey(row);
      if (day) setSearch({ month: monthOfDay(day), day, run: row.runId });
    },
    [setSearch],
  );

  // Resizing the day panel: the width is measured when a drag starts, so the default
  // (a third of the page) works as a starting point too.
  const bodyRef = useRef<HTMLDivElement>(null);
  const [panelWidth, setPanelWidth] = useState(readPanelWidth);
  const resizeStartWidth = useRef(0);
  const maxPanelWidth = () =>
    Math.max(
      PANEL_MIN_WIDTH,
      (bodyRef.current?.clientWidth ?? 0) - CALENDAR_MIN_WIDTH - HANDLE_WIDTH,
    );
  const handleResizeStart = () => {
    const panel = bodyRef.current?.lastElementChild;
    resizeStartWidth.current = panel?.getBoundingClientRect().width ?? PANEL_MIN_WIDTH;
  };
  const handleResize = (deltaX: number) => {
    // The panel is on the right: dragging left widens it.
    const width = Math.min(
      maxPanelWidth(),
      Math.max(PANEL_MIN_WIDTH, resizeStartWidth.current - deltaX),
    );
    setPanelWidth(width);
    storePanelWidth(width);
  };
  const handleResetWidth = () => {
    setPanelWidth(null);
    storePanelWidth(null);
  };

  const [pendingRunId, setPendingRunId] = useState<string | null>(null);
  const handleQueue = useCallback(
    async (runId: string) => {
      setPendingRunId(runId);
      try {
        await triggerPipeline({ run_id: runId });
      } catch {
        // Shown above the calendar via triggerPipelineError.
      } finally {
        setPendingRunId(null);
      }
    },
    [triggerPipeline],
  );

  return (
    <>
      <h1 className="sr-only">Runs</h1>
      <TopBar
        className={styles.topBar}
        actions={<RunSearch rows={runRows} onSelect={handleSearchSelect} />}
      />

      {!runRowsError && penelopeRunsError && (
        <Notice tone="warning" title="Penelope is unavailable">
          Only processed runs are shown. {describeError(penelopeRunsError)}
        </Notice>
      )}
      {!runRowsError && runsError && (
        <Notice tone="warning" title="Processed runs couldn't be loaded">
          Dashboards can't be opened. {describeError(runsError)}
        </Notice>
      )}
      {pipelineRunsError && (
        <Notice tone="warning" title="Pipeline jobs couldn't be loaded">
          Statuses may be out of date. {describeError(pipelineRunsError)}
        </Notice>
      )}
      {triggerPipelineError && (
        <Notice tone="error" title="Couldn't queue the pipeline">
          {describeError(triggerPipelineError)}
        </Notice>
      )}
      {undatedCount > 0 && (
        <Notice tone="info" title="Some runs have no date">
          {undatedCount === 1 ? "1 run has" : `${undatedCount} runs have`} no recorded time, so{" "}
          {undatedCount === 1 ? "it isn't" : "they aren't"} on the calendar.
        </Notice>
      )}

      {runRowsIsLoading ? (
        <LoadingState message="Loading runs…" />
      ) : runRowsError ? (
        <ErrorState error={runRowsError} />
      ) : (
        <div
          ref={bodyRef}
          className={styles.body}
          data-panel-open={selectedDay !== null}
          style={
            panelWidth === null
              ? undefined
              : ({ "--panel-width": `${panelWidth}px` } as CSSProperties)
          }
        >
          <MonthCalendar
            month={month}
            runsByDay={runsByDay}
            selectedDay={selectedDay}
            today={today}
            onSelectDay={handleSelectDay}
            onMonthChange={(delta) => setSearch({ ...search, month: addMonths(month, delta) })}
            onToday={() => setSearch({ ...search, month: toMonthKey(new Date()) })}
          />
          {selectedDay && (
            <ResizeHandle
              className={styles.resizeHandle}
              label="Resize day panel"
              value={panelWidth ?? undefined}
              min={PANEL_MIN_WIDTH}
              max={maxPanelWidth()}
              onResizeStart={handleResizeStart}
              onResize={handleResize}
              onReset={handleResetWidth}
            />
          )}
          {selectedDay && (
            <DayRunsPanel
              day={selectedDay}
              runs={dayRuns}
              selectedRunId={search.run ?? null}
              pendingRunId={pendingRunId}
              onSelectRun={handleSelectRun}
              onQueue={handleQueue}
              onClose={() => setSearch({ month })}
            />
          )}
        </div>
      )}
    </>
  );
}
