import type { PipelineRunResponse } from "@schemas/pipeline.schema";
import { formatDateTime } from "@utils/format";

type PipelineJobStatusProps = {
  job: PipelineRunResponse;
  runLabel: string;
};

const STATUS_TEXT: Record<PipelineRunResponse["status"], string> = {
  queued: "Queued",
  running: "Running…",
  succeeded: "Processed. It's now in the Load list.",
  failed: "Failed",
};

export default function PipelineJobStatus({ job, runLabel }: PipelineJobStatusProps) {
  return (
    <div className="job-status" role="status" aria-live="polite">
      <div className="job-status__header">
        <span className={`badge badge--${job.status}`}>{job.status}</span>
        <span className="job-status__run">{runLabel}</span>
      </div>
      <p className="job-status__text">{STATUS_TEXT[job.status]}</p>
      {job.error && <pre className="job-status__error">{job.error}</pre>}
      <p className="job-status__meta">
        Job {job.id} · queued {formatDateTime(job.queued_at)}
      </p>
    </div>
  );
}
