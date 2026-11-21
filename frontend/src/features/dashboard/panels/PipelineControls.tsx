import Notice from "@components/ui/Notice";
import type { StepState, StepStatus } from "@hooks/usePipelineSteps";
import type { PipelineStep } from "@schemas/pipeline.schema";
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
};

type PipelineStepListProps = {
  steps: StepState[];
  // Queueing failed, e.g. a 409 because the run already has an active job.
  error: unknown;
};

// One row per step: its status, when it last ran, and why it failed.
export function PipelineStepList({ steps, error }: PipelineStepListProps) {
  return (
    <div className={styles.status}>
      <ul className={styles.steps}>
        {steps.map((s) => (
          <li key={s.step} className={styles.step}>
            <span className={styles.stepName}>{STEP_LABEL[s.step]}</span>
            <span className={cx(styles.badge, styles[s.status])}>{STATUS_LABEL[s.status]}</span>
            <span className={styles.meta}>{s.lastRunAt ? formatDateTime(s.lastRunAt) : ""}</span>
            {s.status === "failed" && s.error && (
              <span className={styles.error} title={s.error}>
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
