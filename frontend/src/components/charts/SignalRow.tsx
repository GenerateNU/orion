import type { ComponentPropsWithoutRef } from "react";
import Checkbox from "@components/ui/Checkbox";
import styles from "./SignalRow.module.css";

type SignalRowProps = Omit<ComponentPropsWithoutRef<typeof Checkbox>, "label"> & {
  // A Penelope data type, e.g. "Pack_Current".
  name: string;
  unit?: string;
};

// Figma "Signal Row": State (Default | Hover | Selected). One row of the Add Signal picker;
// a Checkbox, so pass checked + onChange.
export default function SignalRow({ name, unit, ...props }: SignalRowProps) {
  return (
    <Checkbox
      className={styles.row}
      label={
        <>
          <span className={styles.name}>{name}</span>
          {unit && <span className={styles.unit}>{unit}</span>}
        </>
      }
      {...props}
    />
  );
}
