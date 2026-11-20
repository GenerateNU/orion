import type { ComponentPropsWithoutRef, ReactElement, ReactNode } from "react";
import { DropdownMenu } from "radix-ui";
import { cx } from "@utils/classNames";
import styles from "./Menu.module.css";

type MenuProps = {
  // The button that opens the menu, e.g. <IconButton label="Run actions"><MoreHorizontal /></IconButton>.
  trigger: ReactElement;
  children: ReactNode;
  align?: "start" | "center" | "end";
  // preventDefault() here when an item moves focus elsewhere (e.g. opens an input).
  onCloseAutoFocus?: (event: Event) => void;
};

// Figma "Menu": a dropdown of MenuItems, with MenuSeparator between groups.
export default function Menu({ trigger, children, align = "end", onCloseAutoFocus }: MenuProps) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>{trigger}</DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className={styles.menu}
          align={align}
          sideOffset={4}
          onCloseAutoFocus={onCloseAutoFocus}
        >
          {children}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

type MenuItemProps = ComponentPropsWithoutRef<typeof DropdownMenu.Item> & {
  // A lucide icon before the label.
  icon?: ReactNode;
  // Figma State=Danger: destructive actions such as delete.
  danger?: boolean;
};

// Figma "Menu Item": State (Default | Hover | Danger). onSelect runs the action.
export function MenuItem({ icon, danger = false, className, children, ...props }: MenuItemProps) {
  return (
    <DropdownMenu.Item className={cx(styles.item, danger && styles.danger, className)} {...props}>
      {icon}
      {children}
    </DropdownMenu.Item>
  );
}

export function MenuSeparator() {
  return <DropdownMenu.Separator className={styles.separator} />;
}
