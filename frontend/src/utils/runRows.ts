import type { PipelineRunResponse } from "@schemas/pipeline.schema";
import type { RunResponse } from "@schemas/run.schema";

// A run's pipeline status as the UI shows it (Figma "StatusBadge"):
// loaded = processed and ready to open; queued/processing = in the pipeline;
// not-processed = raw data only; failed = the latest pipeline job errored.
export type RunStatus = "loaded" | "processing" | "queued" | "not-processed" | "failed";

// One row of the Runs table: an OrionDB run joined with its latest pipeline job.
export type RunRow = {
  runId: string;
  time: string | null;
  durationS: number | null;
  status: RunStatus;
  // The run has been processed, so its dashboard has data to show.
  canOpen: boolean;
  latestJob: PipelineRunResponse | null;
  // 1-based position in the pipeline queue; set only while status is "queued".
  queuePosition: number | null;
};

type RunRowSources = {
  runs: RunResponse[] | undefined;
  // Newest first, as GET /pipeline/runs returns them.
  jobs: PipelineRunResponse[] | undefined;
};

// The latest job wins: a failed re-run means the stored data may be incomplete.
function statusFor(latestJob: PipelineRunResponse | null, isProcessed: boolean): RunStatus {
  switch (latestJob?.status) {
    case "queued":
      return "queued";
    case "running":
      return "processing";
    case "failed":
      return "failed";
    default:
      return isProcessed ? "loaded" : "not-processed";
  }
}

// Jobs are optional so the table still lists runs when GET /pipeline/runs fails.
export function buildRunRows({ runs = [], jobs = [] }: RunRowSources): RunRow[] {
  const latestJobs = new Map<string, PipelineRunResponse>();
  for (const job of jobs) {
    if (!latestJobs.has(job.run_id)) latestJobs.set(job.run_id, job);
  }

  // The pipeline worker takes queued jobs oldest first.
  const queuePositions = new Map<string, number>();
  jobs
    .filter((job) => job.status === "queued")
    .sort((a, b) => Date.parse(a.queued_at) - Date.parse(b.queued_at))
    .forEach((job, index) => queuePositions.set(job.run_id, index + 1));

  const rows = runs.map((run): RunRow => {
    const latestJob = latestJobs.get(run.run_id) ?? null;
    const status = statusFor(latestJob, run.processed);

    return {
      runId: run.run_id,
      time: run.run_time ?? run.start_time ?? null,
      durationS: run.duration_s,
      status,
      canOpen: run.processed,
      latestJob,
      queuePosition: status === "queued" ? (queuePositions.get(run.run_id) ?? null) : null,
    };
  });

  const timeOf = (row: RunRow) => (row.time ? Date.parse(row.time) : 0);
  return rows.sort((a, b) => timeOf(b) - timeOf(a));
}
