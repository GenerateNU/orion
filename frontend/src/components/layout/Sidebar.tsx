import { Children, useState, type ReactNode } from "react";
import { cx } from "@utils/classNames";
import styles from "./Sidebar.module.css";

type SidebarProps = {
  // NavItems, in order.
  children: ReactNode;
};

// Remembered per browser; a convenience, so a failing storage just means expanded.
const COLLAPSED_KEY = "orion-sidebar-collapsed";

const readCollapsed = () => {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
};

// Figma "Sidebar". Collapses to a thin rail holding only its toggle, to give the
// page more width (on narrow screens it's a top bar and always shown).
export default function Sidebar({ children }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(readCollapsed);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    try {
      localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
    } catch {
      // Not remembered; it still toggles.
    }
  };

  return (
    <aside className={cx(styles.sidebar, collapsed && styles.collapsed)}>
      <button
        type="button"
        className={styles.toggle}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-expanded={!collapsed}
        onClick={toggle}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <rect x="1.75" y="2.75" width="12.5" height="10.5" rx="2" stroke="currentColor" />
          <path d="M6 3v10" stroke="currentColor" />
        </svg>
      </button>
      <nav aria-label="Main" className={styles.nav}>
        <ul className={styles.list}>
          {Children.toArray(children).map((child, index) => (
            <li key={index}>{child}</li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
