import { Children, type ReactNode } from "react";
import styles from "./Sidebar.module.css";

type SidebarProps = {
  // NavItems, in order.
  children: ReactNode;
};

// Figma "Sidebar".
export default function Sidebar({ children }: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <nav aria-label="Main">
        <ul className={styles.list}>
          {Children.toArray(children).map((child, index) => (
            <li key={index}>{child}</li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
