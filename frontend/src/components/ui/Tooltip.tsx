import type { ReactElement, ReactNode } from "react";
import { Tooltip as RadixTooltip } from "radix-ui";
import styles from "./Tooltip.module.css";

type TooltipProps = {
  content: ReactNode;
  // One focusable element (a button, link…) that shows the tooltip on hover/focus.
  children: ReactElement;
  side?: "top" | "right" | "bottom" | "left";
};

// Figma "Tooltip". Needs TooltipProvider (main.tsx) above it.
export default function Tooltip({ content, children, side = "top" }: TooltipProps) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content className={styles.tooltip} side={side} sideOffset={4}>
          {content}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}

export const TooltipProvider = RadixTooltip.Provider;
