import { useEffect, useId, useRef, useState } from "react";
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

type PipelineMenuProps = {
  // A job for this run is queued or running, so nothing new can be queued.
  disabled: boolean;
  onRunStep: (step: PipelineStep) => void;
  onRunAll: () => void;
};

// "Run pipeline" button with a dropdown: each step, then Run all. Closes on a
// choice, Escape, or a click outside.
export function PipelineMenu({ disabled, onRunStep, onRunAll }: PipelineMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const choose = (action: () => void) => {
    setOpen(false);
    action();
  };

  return (
    <div ref={rootRef} className={styles.menuRoot}>
      <Button
        variant="secondary"
        disabled={disabled}
        aria-expanded={open && !disabled}
        aria-controls={menuId}
        onClick={() => setOpen((current) => !current)}
      >
        {disabled ? "Pipeline running…" : "Run pipeline"}
        <span aria-hidden="true">▾</span>
      </Button>
      {open && !disabled && (
        <div id={menuId} className={styles.menu}>
          {PIPELINE_STEPS.map((step) => (
            <button
              key={step}
              type="button"
              className={styles.item}
              onClick={() => choose(() => onRunStep(step))}
            >
              {STEP_LABEL[step]}
            </button>
          ))}
          <hr className={styles.divider} />
          <button type="button" className={styles.item} onClick={() => choose(onRunAll)}>
            Run all
          </button>
        </div>
      )}
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
