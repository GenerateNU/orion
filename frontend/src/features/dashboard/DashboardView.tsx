import { useEffect } from "react";
import { getRouteApi } from "@tanstack/react-router";
import EmptyState from "@components/EmptyState";
import ErrorState from "@components/ErrorState";
import LoadingState from "@components/LoadingState";
import Breadcrumb, { BreadcrumbCurrent, BreadcrumbLink } from "@components/layout/Breadcrumb";
import PageHeader from "@components/layout/PageHeader";
import StatusBadge from "@components/runs/StatusBadge";
import { ButtonLink } from "@components/ui/Button";
import { ApiError } from "@api/client";
import { formatDate, formatDuration } from "@utils/format";
import DashboardStoreProvider from "@features/dashboard/state/DashboardStoreProvider";
import { useLastRunStore } from "@features/dashboard/state/lastRunStore";
import {
  useCommittedWindow,
  useDashboardRun,
  useSelectedLaps,
} from "@features/dashboard/state/useDashboard";
import styles from "./DashboardView.module.css";

const dashboardRoute = getRouteApi("/runs/$runId/dashboard");

// Route component for /runs/$runId/dashboard. Keyed by run id so another run
// starts with a fresh interaction store.
export default function DashboardView() {
  const { runId } = dashboardRoute.useParams();
  return (
    <DashboardStoreProvider key={runId}>
      <RunDashboard />
    </DashboardStoreProvider>
  );
}

// Figma "Run Dashboard — Placeholder". Charts, track map and sensor panels go in
// the placeholder panel once they're designed; each reads shared state through
// state/useDashboard.ts and data through data/useDashboardData.ts.
function RunDashboard() {
  const { runId, run, runIsLoading, runError } = useDashboardRun();

  const setLastRunId = useLastRunStore((state) => state.setLastRunId);
  useEffect(() => {
    if (run) setLastRunId(run.run_id);
  }, [run, setLastRunId]);

  const breadcrumb = (
    <Breadcrumb>
      <BreadcrumbLink to="/runs">Runs</BreadcrumbLink>
      <BreadcrumbCurrent mono>{runId}</BreadcrumbCurrent>
    </Breadcrumb>
  );

  if (runIsLoading) {
    return (
      <>
        {breadcrumb}
        <LoadingState message="Loading run…" />
      </>
    );
  }

  if (!run) {
    const notFound = runError instanceof ApiError && runError.status === 404;
    return (
      <>
        {breadcrumb}
        <PageHeader title="Dashboard" />
        {notFound || !runError ? (
          <EmptyState message="This run hasn't been processed. Queue its pipeline from Runs." />
        ) : (
          <ErrorState error={runError} />
        )}
      </>
    );
  }

  return (
    <>
      {breadcrumb}
      <PageHeader
        variant="entity"
        title={run.run_id}
        badge={<StatusBadge status="loaded" />}
        description={`${formatDate(run.run_time ?? run.start_time)} · ${formatDuration(run.duration_s)}`}
        actions={
          <ButtonLink variant="secondary" to="/runs">
            <span aria-hidden="true">←</span> Back to runs
          </ButtonLink>
        }
      />
      <section className={styles.placeholder} aria-labelledby="run-dashboard-title">
        <h2 id="run-dashboard-title" className={styles.placeholderTitle}>
          Run dashboard
        </h2>
        <p className={styles.placeholderText}>
          Charts, track map and sensor panels for this run will be designed here.
        </p>
        <SelectionSummary />
      </section>
    </>
  );
}

const formatRunTime = (ms: number) => formatDuration(ms / 1000);

// Temporary: shows the shared selection until panels exist to show it.
function SelectionSummary() {
  const window = useCommittedWindow();
  const laps = useSelectedLaps();
  const windowLabel = window
    ? `${formatRunTime(window[0])}–${formatRunTime(window[1])}`
    : "whole run";
  const lapsLabel = laps.length > 0 ? laps.join(", ") : "none";

  return (
    <p className={styles.placeholderText}>
      Window: {windowLabel} · Laps: {lapsLabel}
    </p>
  );
}
