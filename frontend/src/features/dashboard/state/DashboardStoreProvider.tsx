import { useState, type ReactNode } from "react";
import {
  createDashboardStore,
  DashboardStoreContext,
} from "@features/dashboard/state/dashboardStore";

// Give it `key={runId}` so opening another run starts from a fresh store.
export default function DashboardStoreProvider({ children }: { children: ReactNode }) {
  const [store] = useState(createDashboardStore);
  return <DashboardStoreContext.Provider value={store}>{children}</DashboardStoreContext.Provider>;
}
