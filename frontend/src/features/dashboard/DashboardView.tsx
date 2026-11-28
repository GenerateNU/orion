import { getRouteApi } from "@tanstack/react-router";
import EmptyState from "@components/ui/EmptyState";
import ErrorState from "@components/ui/ErrorState";
import LoadingState from "@components/ui/LoadingState";
import Breadcrumb, { BreadcrumbCurrent, BreadcrumbLink } from "@components/layout/Breadcrumb";
import PageHeader from "@components/layout/PageHeader";
import StatusBadge from "@components/runs/StatusBadge";
import Button, { ButtonLink } from "@components/ui/Button";
import { ApiError } from "@api/client";
import { cx } from "@utils/classNames";
import { formatDate, formatDuration } from "@utils/format";
import DashboardStoreProvider from "@features/dashboard/state/DashboardStoreProvider";
import { useDashboardRun } from "@features/dashboard/state/useDashboard";
import styles from "./DashboardView.module.css";
import GpsToggle from "@features/dashboard/panels/GpsToggle";
import { TrackMap } from "@features/dashboard/panels/TrackMap";
import { useRunPipeline } from "@hooks/useRunPipeline";
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
  const pipeline = useRunPipeline(runId);

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
          <div className={styles.actions}>
            <Button disabled={pipeline.isBusy} onClick={pipeline.runPipeline}>
              {pipeline.isBusy ? "Running…" : "Run pipeline"}
            </Button>
            <ButtonLink variant="secondary" to="/runs">
              <span aria-hidden="true">←</span> Back to runs
            </ButtonLink>
          </div>
        }
      />

      <div className={styles.layout}>
        <section className={styles.panel} aria-labelledby="track-map-heading">
          <div className={styles.panelHeader}>
            <h2 id="track-map-heading" className={styles.panelHeading}>
              Track position
            </h2>
            <GpsToggle />
          </div>
          <TrackMap />
        </section>
        <section className={cx(styles.panel, styles.right)} aria-labelledby="sensor-charts-heading">
          <h2 id="sensor-charts-heading" className={styles.visuallyHidden}>
            Sensors
          </h2>
          <SensorChartsPanel />
        </section>
      </div>
    </>
  );
}
