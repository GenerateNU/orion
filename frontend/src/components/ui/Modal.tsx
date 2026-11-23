import type { ReactElement, ReactNode } from "react";
import { Dialog } from "radix-ui";
import { X } from "lucide-react";
import IconButton from "./IconButton";
import styles from "./Modal.module.css";

type ModalProps = {
  title: string;
  children: ReactNode;
  // Actions at the bottom right, e.g. a ghost Cancel and a primary Confirm.
  footer?: ReactNode;
  // Controlled: pass open + onOpenChange. Uncontrolled: pass trigger.
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  // The button that opens the modal.
  trigger?: ReactElement;
};

// Figma "Modal". Wrap a footer button in <ModalClose> to close on click.
export default function Modal({
  title,
  children,
  footer,
  open,
  onOpenChange,
  trigger,
}: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}
      <Dialog.Portal>
        <Dialog.Overlay className={styles.overlay} />
        <Dialog.Content
          className={styles.modal}
          aria-describedby={undefined}
          // Focus the dialog, not the close button, so its tooltip doesn't pop up on open.
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            (event.currentTarget as HTMLElement).focus();
          }}
        >
          <header className={styles.header}>
            <Dialog.Title className={styles.title}>{title}</Dialog.Title>
            <Dialog.Close asChild>
              <IconButton label="Close">
                <X />
              </IconButton>
            </Dialog.Close>
          </header>
          <div className={styles.body}>{children}</div>
          {footer && <footer className={styles.footer}>{footer}</footer>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// Closes the surrounding Modal when its child (a Button) is clicked.
export function ModalClose({ children }: { children: ReactElement }) {
  return <Dialog.Close asChild>{children}</Dialog.Close>;
}
