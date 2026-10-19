import { useCallback, useState } from "react";
import EmptyState from "@components/EmptyState";
import ErrorState from "@components/ErrorState";
import LoadingState from "@components/LoadingState";
import PageHeader from "@components/layout/PageHeader";
import RunsTable from "@components/runs/RunsTable";
import Notice from "@components/ui/Notice";
import Pagination from "@components/ui/Pagination";
import { usePagination } from "@hooks/usePagination";
import { usePipelineMutations } from "@hooks/usePipelineRuns";
import { useRunRows } from "@hooks/useRunRows";
import { describeError } from "@utils/describeError";

const PAGE_SIZE = 8;

// Figma "Runs — Landing": every run, its pipeline status and the next action.
export default function RunsView() {
  const { runRows, runRowsIsLoading, runRowsError, penelopeRunsError, runsError, pipelineRunsError } =
    useRunRows();
  const { triggerPipeline, triggerPipelineError } = usePipelineMutations();
  const { page, pageCount, pageItems, setPage, firstItem, lastItem } = usePagination(runRows, PAGE_SIZE);

  const [pendingRunId, setPendingRunId] = useState<string | null>(null);
  const handleQueue = useCallback(
    async (runId: string) => {
      setPendingRunId(runId);
      try {
        await triggerPipeline({ run_id: runId });
      } catch {
        // Shown above the table via triggerPipelineError.
      } finally {
        setPendingRunId(null);
      }
    },
    [triggerPipeline],
  );

  const placeholder = runRowsIsLoading ? (
    <LoadingState message="Loading runs…" />
  ) : runRowsError ? (
    <ErrorState error={runRowsError} />
  ) : runRows.length === 0 ? (
    <EmptyState message="No runs yet. Runs recorded in Penelope will appear here." />
  ) : undefined;

  return (
    <>
      <PageHeader
        title="Runs"
        description="Queue a pipeline to process a run. Open a loaded run to view its dashboard."
      />

      {!runRowsError && penelopeRunsError && (
        <Notice tone="warning">
          Penelope is unavailable, so only processed runs are listed. {describeError(penelopeRunsError)}
        </Notice>
      )}
      {!runRowsError && runsError && (
        <Notice tone="warning">
          Processed runs couldn't be loaded, so dashboards can't be opened. {describeError(runsError)}
        </Notice>
      )}
      {pipelineRunsError && (
        <Notice tone="warning">
          Pipeline jobs couldn't be loaded, so statuses may be out of date. {describeError(pipelineRunsError)}
        </Notice>
      )}
      {triggerPipelineError && <Notice tone="error">{describeError(triggerPipelineError)}</Notice>}

      <RunsTable
        rows={pageItems}
        pendingRunId={pendingRunId}
        placeholder={placeholder}
        onQueue={handleQueue}
        summary={!placeholder && `Showing ${firstItem}–${lastItem} of ${runRows.length} runs`}
        pagination={
          !placeholder && (
            <Pagination page={page} pageCount={pageCount} onPageChange={setPage} label="Runs pages" />
          )
        }
      />
    </>
  );
}
