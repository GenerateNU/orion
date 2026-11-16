import Button from "@components/ui/Button";
import Notice from "@components/ui/Notice";
import type { StepState, StepStatus } from "@hooks/usePipelineSteps";
import { PIPELINE_STEPS, type PipelineStep } from "@schemas/pipeline.schema";
import { cx } from "@utils/classNames";
import { describeError } from "@utils/describeError";
import { formatDateTime } from "@utils/format";
import styles from "./PipelineControls.module.css";

const STEP_LABEL: Record<PipelineStep, string> = {
  clean_step: "Clean",
  state_step: "Estimate",
  lap_step: "Laps",
};

const STATUS_LABEL: Record<StepStatus, string> = {
  idle: "Not run",
  running: "Running…",
  succeeded: "Succeeded",
  failed: "Failed",
  skipped: "Skipped",
};

type PipelineButtonsProps = {
  // A job for this run is queued or running, so nothing new can be queued.
  disabled: boolean;
  onRunStep: (step: PipelineStep) => void;
  onRunAll: () => void;
};

// A button per step, then Run all. All disabled while a job for the run is active.
export function PipelineButtons({ disabled, onRunStep, onRunAll }: PipelineButtonsProps) {
  return (
    <div className={styles.buttons} role="group" aria-label="Run pipeline">
      {PIPELINE_STEPS.map((step) => (
        <Button key={step} variant="secondary" disabled={disabled} onClick={() => onRunStep(step)}>
          {STEP_LABEL[step]}
        </Button>
      ))}
      <Button disabled={disabled} onClick={onRunAll}>
        Run all
      </Button>
    </div>
  );
}

type PipelineStepListProps = {
  steps: StepState[];
  // Queueing failed, e.g. a 409 because the run already has an active job.
  error: unknown;
};

// One row per step: its status, when it last ran, and why it failed or is out of date.
export function PipelineStepList({ steps, error }: PipelineStepListProps) {
  return (
    <div className={styles.status}>
      <ul className={styles.steps}>
        {steps.map((s) => (
          <li key={s.step} className={styles.step}>
            <span className={styles.stepName}>{STEP_LABEL[s.step]}</span>
            <span className={cx(styles.badge, styles[s.status])}>{STATUS_LABEL[s.status]}</span>
            <span className={styles.meta}>{s.lastRunAt ? formatDateTime(s.lastRunAt) : ""}</span>
            {s.stale && s.status === "succeeded" && (
              <span className={styles.note}>Out of date: an earlier step ran since</span>
            )}
            {s.status === "failed" && s.error && (
              <span className={cx(styles.note, styles.error)} title={s.error}>
                {s.error}
              </span>
            )}
          </li>
        ))}
      </ul>
      {error !== null && <Notice tone="error">{describeError(error)}</Notice>}
    </div>
  );
}
