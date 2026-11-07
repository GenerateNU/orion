import { createContext, useContext } from "react";
import { createStore, type StoreApi } from "zustand";
import type { ProgressRange } from "@features/dashboard/utils/progress";
import type { RunTime, TimeWindow } from "@features/dashboard/utils/time";

// Transient interaction state shared by the dashboard's panels: what the pointer is
// over and the window being dragged. Durable selection (laps, committed window)
// lives in the URL instead (utils/search.ts). Panels reach both through
// useDashboard.ts, never through this store directly.
export type DashboardInteraction = {
  // Run time under the pointer in any chart or the track map; drives synced
  // crosshairs and the car marker. Changes up to once a frame.
  hoverTime: RunTime | null;
  // Lap under the pointer in the lap list or on the map.
  hoverLap: number | null;
  // Live while a brush is dragged; committed to the URL on release.
  draftWindow: TimeWindow | null;
  // Lap progress under the pointer in a progress chart. Changes up to once a frame.
  hoverProgress: number | null;
  // Live while a progress range is dragged; committed to the URL on release.
  draftProgressRange: ProgressRange | null;

  setHoverTime: (time: RunTime | null) => void;
  setHoverLap: (lap: number | null) => void;
  setDraftWindow: (window: TimeWindow | null) => void;
  setHoverProgress: (progress: number | null) => void;
  setDraftProgressRange: (range: ProgressRange | null) => void;
};

export type DashboardStore = StoreApi<DashboardInteraction>;

// One store per opened run (DashboardStoreProvider is keyed by run id), so hover
// and drafts never carry over to another run.
export const createDashboardStore = (): DashboardStore =>
  createStore<DashboardInteraction>()((set) => ({
    hoverTime: null,
    hoverLap: null,
    draftWindow: null,
    hoverProgress: null,
    draftProgressRange: null,
    setHoverTime: (hoverTime) => set({ hoverTime }),
    setHoverLap: (hoverLap) => set({ hoverLap }),
    setDraftWindow: (draftWindow) => set({ draftWindow }),
    setHoverProgress: (hoverProgress) => set({ hoverProgress }),
    setDraftProgressRange: (draftProgressRange) => set({ draftProgressRange }),
  }));

export const DashboardStoreContext = createContext<DashboardStore | null>(null);

export const useDashboardStoreApi = (): DashboardStore => {
  const store = useContext(DashboardStoreContext);
  if (!store) {
    throw new Error("Dashboard hooks must be used inside <DashboardStoreProvider>");
  }
  return store;
};
