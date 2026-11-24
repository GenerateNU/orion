import { useEffect, useRef } from "react";
import { Outlet, useLocation } from "@tanstack/react-router";
import styles from "./App.module.css";

// The app shell (root route): the current route's view, full width. Each view brings
// its own header (the Runs TopBar, the dashboard's Breadcrumb).
export default function App() {
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
    <main ref={mainRef} className={styles.main} tabIndex={-1}>
      <Outlet />
    </main>
  );
}
