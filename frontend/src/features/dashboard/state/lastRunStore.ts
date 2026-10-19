import { create } from "zustand";

// The last run opened on the dashboard, so the sidebar's Dashboard item can link
// back to it from other pages. Not persisted: after a reload it is set again when
// a dashboard opens.
type LastRunState = {
  lastRunId: string | null;
  setLastRunId: (runId: string) => void;
};

export const useLastRunStore = create<LastRunState>()((set) => ({
  lastRunId: null,
  setLastRunId: (lastRunId) => set({ lastRunId }),
}));
