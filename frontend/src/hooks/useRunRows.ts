import { useMemo } from "react";
import type { PipelineRunFilters } from "@schemas/pipeline.schema";
import type { RunListFilters } from "@schemas/run.schema";
import { usePenelopeRuns } from "@hooks/usePenelopeRuns";
import { usePipelineRuns } from "@hooks/usePipelineRuns";
import { useRuns } from "@hooks/useRuns";
import { buildRunRows } from "@utils/runRows";

const PROCESSED_ONLY: RunListFilters = { processed: true };
// The backend maximum; enough to cover every queued/running job and recent failures.
const RECENT_JOBS: PipelineRunFilters = { limit: 200 };

// Hook for the Runs table: every run with its pipeline status, newest first.
// One failed source doesn't hide the others; each error is returned separately.
export const useRunRows = () => {
  const { penelopeRuns, penelopeRunsIsLoading, penelopeRunsError } = usePenelopeRuns();
  const { runs, runsIsLoading, runsError } = useRuns(PROCESSED_ONLY);
  const { pipelineRuns, pipelineRunsIsLoading, pipelineRunsError } = usePipelineRuns(RECENT_JOBS);

  const runRows = useMemo(
    () => buildRunRows({ penelopeRuns, processedRuns: runs, jobs: pipelineRuns }),
    [penelopeRuns, runs, pipelineRuns],
  );

  return {
    runRows,
    runRowsIsLoading: penelopeRunsIsLoading || runsIsLoading || pipelineRunsIsLoading,
    // Set only when neither source of runs answered, so there is nothing to list.
    runRowsError: penelopeRunsError && runsError ? runsError : null,
    penelopeRunsError,
    runsError,
    pipelineRunsError,
  };
};
