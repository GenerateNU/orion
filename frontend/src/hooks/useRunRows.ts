import { useMemo } from "react";
import type { PipelineRunFilters } from "@schemas/pipeline.schema";
import { usePipelineRuns } from "@hooks/usePipelineRuns";
import { useRuns } from "@hooks/useRuns";
import { buildRunRows } from "@utils/runRows";

// The backend maximum; enough to cover every queued/running job and recent failures.
const RECENT_JOBS: PipelineRunFilters = { limit: 200 };

// Hook for the Runs table: every run stored in OrionDB with its pipeline status,
// newest first. Penelope isn't read here; POST /runs/sync copies its runs in.
export const useRunRows = () => {
  const { runs, runsIsLoading, runsError } = useRuns();
  const { pipelineRuns, pipelineRunsIsLoading, pipelineRunsError } = usePipelineRuns(RECENT_JOBS);

  const runRows = useMemo(() => buildRunRows({ runs, jobs: pipelineRuns }), [runs, pipelineRuns]);

  return {
    runRows,
    runRowsIsLoading: runsIsLoading || pipelineRunsIsLoading,
    // Without the run list there is nothing to show; job errors only affect statuses.
    runRowsError: runsError,
    pipelineRunsError,
  };
};
