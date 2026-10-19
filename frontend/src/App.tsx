import { useEffect, useRef } from "react";
import { Outlet, useLocation } from "@tanstack/react-router";
import NavItem, { NavItemUnavailable } from "@components/layout/NavItem";
import Sidebar from "@components/layout/Sidebar";
import { useLastRunStore } from "@features/dashboard/state/lastRunStore";
import styles from "./App.module.css";

// The app shell (root route): sidebar plus the current route's view.
export default function App() {
  const lastRunId = useLastRunStore((state) => state.lastRunId);
  const mainRef = useRef<HTMLElement>(null);

  // Move focus to the new view so keyboard and screen reader users land on it.
  // Only on page changes: search-param changes (lap or window selection) keep focus.
  const pathname = useLocation({ select: (location) => location.pathname });
  const previousPathname = useRef(pathname);
  useEffect(() => {
    if (pathname === previousPathname.current) return;
    previousPathname.current = pathname;
    mainRef.current?.focus();
  }, [pathname]);

  return (
    <div className={styles.shell}>
      <Sidebar>
        <NavItem to="/runs" activeOptions={{ exact: true }}>
          Runs
        </NavItem>
        <NavItem
          to="/runs/$runId/dashboard"
          params={{ runId: lastRunId ?? "" }}
          activeOptions={{ includeSearch: false }}
          disabled={!lastRunId}
          title={lastRunId ? undefined : "Open a run first"}
        >
          Dashboard
        </NavItem>
        <NavItemUnavailable title="Not available yet">Pipelines</NavItemUnavailable>
        <NavItemUnavailable title="Not available yet">Settings</NavItemUnavailable>
      </Sidebar>
      <main ref={mainRef} className={styles.main} tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
