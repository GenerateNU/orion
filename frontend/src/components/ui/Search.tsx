import { useEffect, useRef, type ComponentPropsWithoutRef } from "react";
import { Search as SearchIcon } from "lucide-react";
import { cx } from "@utils/classNames";
import inputStyles from "./Input.module.css";
import styles from "./Search.module.css";

type SearchProps = Omit<ComponentPropsWithoutRef<"input">, "type"> & {
  // Accessible name; the placeholder alone isn't one.
  "aria-label": string;
  // ⌘K / Ctrl+K focuses this field and the hint is shown. One per page.
  shortcut?: boolean;
};

// Figma "Search": a pill-shaped search field.
export default function Search({ shortcut = false, className, ...props }: SearchProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!shortcut) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [shortcut]);

  return (
    <div className={cx(styles.search, className)}>
      <SearchIcon aria-hidden="true" />
      <input ref={inputRef} type="search" className={inputStyles.input} {...props} />
      {shortcut && (
        <kbd className={styles.kbd} aria-hidden="true">
          ⌘K
        </kbd>
      )}
    </div>
  );
}
