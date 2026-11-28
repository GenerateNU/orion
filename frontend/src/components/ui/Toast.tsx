import { Toast as RadixToast } from "radix-ui";
import { CircleCheck, CircleX, Info, X } from "lucide-react";
import { cx } from "@utils/classNames";
import IconButton from "./IconButton";
import { dismissToast, useToastStore } from "./toastStore";
import styles from "./Toast.module.css";

const ICON = { success: CircleCheck, error: CircleX, info: Info };

// Figma "Toast": Type (Success | Error | Info). Render once at the app root.
export default function Toaster() {
  const toasts = useToastStore((state) => state.toasts);

  return (
    <RadixToast.Provider>
      {toasts.map(({ id, type, message }) => {
        const Icon = ICON[type];
        return (
          <RadixToast.Root
            key={id}
            className={styles.toast}
            type={type === "error" ? "foreground" : "background"}
            onOpenChange={(open) => !open && dismissToast(id)}
          >
            <Icon className={cx(styles.icon, styles[type])} aria-hidden="true" />
            <RadixToast.Description className={styles.message}>{message}</RadixToast.Description>
            <RadixToast.Close asChild>
              <IconButton label="Dismiss">
                <X />
              </IconButton>
            </RadixToast.Close>
          </RadixToast.Root>
        );
      })}
      <RadixToast.Viewport className={styles.viewport} />
    </RadixToast.Provider>
  );
}
