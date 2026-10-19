import { Children, type ComponentPropsWithRef, type ReactNode } from "react";
import { createLink } from "@tanstack/react-router";
import { cx } from "@utils/classNames";
import styles from "./Breadcrumb.module.css";

type BreadcrumbProps = {
  // BreadcrumbLinks, then a BreadcrumbCurrent for the current page.
  children: ReactNode;
};

export default function Breadcrumb({ children }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className={styles.list}>
        {Children.toArray(children).map((child, index) => (
          <li key={index} className={styles.item}>
            {child}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function BreadcrumbAnchor({ className, ...props }: ComponentPropsWithRef<"a">) {
  return <a className={cx(styles.link, className)} {...props} />;
}

// A crumb for an ancestor page: a router link.
export const BreadcrumbLink = createLink(BreadcrumbAnchor);

type BreadcrumbCurrentProps = {
  children: ReactNode;
  // Monospace, for identifiers such as run ids.
  mono?: boolean;
};

// The last crumb: the current page.
export function BreadcrumbCurrent({ children, mono = false }: BreadcrumbCurrentProps) {
  return (
    <span className={cx(mono && styles.mono)} aria-current="page">
      {children}
    </span>
  );
}
