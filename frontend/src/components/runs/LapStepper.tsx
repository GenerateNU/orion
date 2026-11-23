import { ChevronLeft, ChevronRight } from "lucide-react";
import IconButton from "@components/ui/IconButton";
import styles from "./LapStepper.module.css";

type LapStepperProps = {
  // What's shown, e.g. "Lap 4 of 11" (Mode=Single) or "3 laps, 4, 7, 9" (Mode=Compare).
  label: string;
  // Leave out at the first/last lap to disable that arrow.
  onPrevious?: () => void;
  onNext?: () => void;
};

// Figma "Lap Stepper": Mode (Single | Compare). Steps through laps with the arrows.
export default function LapStepper({ label, onPrevious, onNext }: LapStepperProps) {
  return (
    <div className={styles.stepper}>
      <IconButton label="Previous lap" onClick={onPrevious} disabled={!onPrevious}>
        <ChevronLeft />
      </IconButton>
      <span className={styles.label} aria-live="polite">
        {label}
      </span>
      <IconButton label="Next lap" onClick={onNext} disabled={!onNext}>
        <ChevronRight />
      </IconButton>
    </div>
  );
}
