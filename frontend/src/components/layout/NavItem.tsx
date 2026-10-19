import type { ComponentPropsWithRef, ReactNode } from "react";
import { createLink, type LinkComponent } from "@tanstack/react-router";
import { cx } from "@utils/classNames";
import styles from "./NavItem.module.css";

function NavItemAnchor({ className, ...props }: ComponentPropsWithRef<"a">) {
  return <a className={cx(styles.navItem, className)} {...props} />;
}

const NavItemLink = createLink(NavItemAnchor);

// Figma "NavItem" (State=Default / Active): a router link, active while its route
// is open (exposed as aria-current="page"). `disabled` renders it without an href;
// give a `title` saying why.
const NavItem: LinkComponent<typeof NavItemAnchor> = (props) => (
  <NavItemLink activeProps={{ className: styles.active }} {...props} />
);

export default NavItem;

type NavItemUnavailableProps = {
  children: ReactNode;
  // Why it can't be opened, shown as a tooltip.
  title: string;
};

// A nav item for a page that doesn't exist yet: styled like a disabled NavItem.
export function NavItemUnavailable({ children, title }: NavItemUnavailableProps) {
  return (
    <a className={styles.navItem} role="link" aria-disabled="true" title={title}>
      {children}
    </a>
  );
}
