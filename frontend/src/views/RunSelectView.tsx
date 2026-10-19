import { useState } from "react";
import EmptyState from "@components/EmptyState";
import ErrorState from "@components/ErrorState";
import LoadingState from "@components/LoadingState";
import PenelopeRunPicker from "@components/PenelopeRunPicker";
import PipelineJobStatus from "@components/PipelineJobStatus";
import ProcessedRunPicker from "@components/ProcessedRunPicker";
import { useCurrentRun } from "@hooks/useCurrentRun";
import { usePenelopeRuns } from "@hooks/usePenelopeRuns";
import { usePipelineMutations, usePipelineRun } from "@hooks/usePipelineRuns";
import { useRuns } from "@hooks/useRuns";
import { formatRunLabel } from "@utils/format";

export default function RunSelectView() {
  const { currentRun, setCurrentRun } = useCurrentRun();
  const { runs, runsIsLoading, runsError } = useRuns({ processed: true });
  const { penelopeRuns, penelopeRunsIsLoading, penelopeRunsError } = usePenelopeRuns();
  const { triggerPipeline, isTriggeringPipeline, triggerPipelineError } = usePipelineMutations();

  const [jobId, setJobId] = useState<number>();
  const { pipelineRun, pipelineRunError } = usePipelineRun(jobId);

  const handleProcess = async (runId: string) => {
    try {
      const job = await triggerPipeline({ run_id: runId });
      setJobId(job.id);
    } catch {
      // Shown below via triggerPipelineError.
    }
  };

  const jobRun = penelopeRuns?.find((run) => run.run_id === pipelineRun?.run_id);

  return (
    <div className="run-select">
      <section className="panel">
        <h2 className="panel__title">Load a processed run</h2>
        <p className="panel__hint">Runs that have been through the pipeline successfully.</p>
        {runsIsLoading && <LoadingState message="Loading processed runs…" />}
        {runsError && <ErrorState error={runsError} />}
        {runs &&
          (runs.length === 0 ? (
            <EmptyState message="No processed runs yet. Process one to get started." />
          ) : (
            <ProcessedRunPicker
              runs={runs}
              currentRunId={currentRun?.run_id ?? null}
              onLoad={setCurrentRun}
            />
          ))}
      </section>

      <section className="panel">
        <h2 className="panel__title">Process a run</h2>
        <p className="panel__hint">Send a run from Penelope through the pipeline.</p>
        {penelopeRunsIsLoading && <LoadingState message="Loading runs from Penelope…" />}
        {penelopeRunsError && <ErrorState error={penelopeRunsError} />}
        {penelopeRuns &&
          (penelopeRuns.length === 0 ? (
            <EmptyState message="Penelope has no runs." />
          ) : (
            <PenelopeRunPicker
              runs={penelopeRuns}
              isSubmitting={isTriggeringPipeline}
              onProcess={handleProcess}
            />
          ))}
        {triggerPipelineError && <ErrorState error={triggerPipelineError} />}
        {pipelineRunError && <ErrorState error={pipelineRunError} />}
        {pipelineRun && (
          <PipelineJobStatus
            job={pipelineRun}
            runLabel={jobRun ? formatRunLabel(jobRun) : pipelineRun.run_id}
          />
        )}
      </section>
    </div>
  );
}
