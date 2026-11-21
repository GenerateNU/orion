import type { ComponentPropsWithoutRef } from "react";
import { Search as SearchIcon } from "lucide-react";
import { cx } from "@utils/classNames";
import inputStyles from "./Input.module.css";
import styles from "./Search.module.css";

type SearchProps = Omit<ComponentPropsWithoutRef<"input">, "type"> & {
  // Accessible name; the placeholder alone isn't one.
  "aria-label": string;
};

// Figma "Search": a pill-shaped search field.
export default function Search({ className, ...props }: SearchProps) {
  return (
    <div className={cx(styles.search, className)}>
      <SearchIcon aria-hidden="true" />
      <input type="search" className={inputStyles.input} {...props} />
    </div>
  );
}
