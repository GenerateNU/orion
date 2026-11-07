import { useEffect } from "react";
import { getRouteApi } from "@tanstack/react-router";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import Breadcrumb, { BreadcrumbCurrent, BreadcrumbLink } from "@components/layout/Breadcrumb";
import PageHeader from "@components/layout/PageHeader";
import StatusBadge from "@components/runs/StatusBadge";
import { ButtonLink } from "@components/ui/Button";
import { ApiError } from "@api/client";
import { formatDate, formatDuration } from "@utils/format";
import DashboardStoreProvider from "@features/dashboard/state/DashboardStoreProvider";
import { useLastRunStore } from "@features/dashboard/state/lastRunStore";
import { useDashboardRun } from "@features/dashboard/state/useDashboard";
import styles from "./DashboardView.module.css";
import { TrackMap } from "@features/dashboard/panels/TrackMap";
import SensorChartsPanel from "@components/charts/SensorChartPanel";

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

// The run dashboard: the track map beside the sensor charts. Each panel reads shared state through
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

      <div className={styles.layout}>
        <section className={styles.panel} aria-labelledby="track-map-heading">
          <h2 id="track-map-heading" className={styles.panelHeading}>
            Track position
          </h2>
          <TrackMap />
        </section>
        <section className={styles.panel} aria-labelledby="sensor-charts-heading">
          <h2 id="sensor-charts-heading" className={styles.panelHeading}>
            Sensors
          </h2>
          <SensorChartsPanel />
        </section>
      </div>
    </>
  );
}
