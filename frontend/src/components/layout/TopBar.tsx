import { Children, type ComponentPropsWithRef, type ReactNode } from "react";
import { createLink, type LinkComponent } from "@tanstack/react-router";
import { cx } from "@utils/classNames";
import logoUrl from "../../assets/orion-logo.svg";
import styles from "./TopBar.module.css";

type TopBarProps = {
  // Left, after the logo: a TopBarNav (Figma Context=Library) or a Breadcrumb (Context=Run).
  // Leave out for just the logo (Figma Runs · Calendar).
  children?: ReactNode;
  // Right-aligned: e.g. Search and Avatar, or a Share Button and Avatar.
  actions?: ReactNode;
};

// Figma "Top Bar": the Orion logo, then page navigation, then actions.
export default function TopBar({ children, actions }: TopBarProps) {
  return (
    <header className={styles.topBar}>
      <span className={styles.logo}>
        <img src={logoUrl} alt="" width={33} height={18} />
        Orion
      </span>
      <span className={styles.divider} aria-hidden="true" />
      {children}
      {actions && <div className={styles.actions}>{actions}</div>}
    </header>
  );
}

// The Library context's links: TopBarLinks, in order.
export function TopBarNav({ children }: { children: ReactNode }) {
  return (
    <nav aria-label="Main">
      <ul className={styles.nav}>
        {Children.toArray(children).map((child, index) => (
          <li key={index}>{child}</li>
        ))}
      </ul>
    </nav>
  );
}

function TopBarAnchor({ className, ...props }: ComponentPropsWithRef<"a">) {
  return <a className={cx(styles.link, className)} {...props} />;
}

const TopBarLinkBase = createLink(TopBarAnchor);

// A router link, highlighted while its route is open (aria-current="page").
export const TopBarLink: LinkComponent<typeof TopBarAnchor> = (props) => (
  <TopBarLinkBase activeProps={{ className: styles.active }} {...props} />
);
