import { useId } from "react";
import { Select as RadixSelect } from "radix-ui";
import { Check, ChevronDown } from "lucide-react";
import { cx } from "@utils/classNames";
import fieldStyles from "./Field.module.css";
import styles from "./Select.module.css";

export type SelectOption = { value: string; label: string };

type SelectProps = {
  options: readonly SelectOption[];
  value?: string;
  onValueChange?: (value: string) => void;
  // Shown above the field. Without it, pass an aria-label.
  label?: string;
  "aria-label"?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
};

// Figma "Select": State (Default | Open | Disabled). The open list uses the Menu look.
export default function Select({
  options,
  value,
  onValueChange,
  label,
  "aria-label": ariaLabel,
  placeholder,
  disabled,
  className,
}: SelectProps) {
  const id = useId();

  return (
    <div className={cx(fieldStyles.wrapper, className)}>
      {label && (
        <label className={fieldStyles.label} htmlFor={id}>
          {label}
        </label>
      )}
      <RadixSelect.Root value={value} onValueChange={onValueChange} disabled={disabled}>
        <RadixSelect.Trigger
          id={id}
          aria-label={ariaLabel}
          className={cx(fieldStyles.field, styles.trigger)}
        >
          <span className={styles.value}>
            <RadixSelect.Value placeholder={placeholder} />
          </span>
          <RadixSelect.Icon asChild>
            <ChevronDown className={styles.chevron} />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content className={styles.content} position="popper" sideOffset={4}>
            <RadixSelect.Viewport>
              {options.map((option) => (
                <RadixSelect.Item key={option.value} value={option.value} className={styles.item}>
                  <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator className={styles.indicator}>
                    <Check />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    </div>
  );
}
