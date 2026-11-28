import { create } from "zustand";

export type ToastType = "success" | "error" | "info";

export type ToastItem = { id: number; type: ToastType; message: string };

// The open toasts, rendered by <Toaster /> (Toast.tsx).
export const useToastStore = create<{ toasts: ToastItem[] }>(() => ({ toasts: [] }));

let nextId = 0;

// Shows a short message in the corner, e.g. showToast("success", "Link copied").
// Callable from anywhere: event handlers, mutation callbacks…
export function showToast(type: ToastType, message: string) {
  useToastStore.setState((state) => ({
    toasts: [...state.toasts, { id: nextId++, type, message }],
  }));
}

export function dismissToast(id: number) {
  useToastStore.setState((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
}
