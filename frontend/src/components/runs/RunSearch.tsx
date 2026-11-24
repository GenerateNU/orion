import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import RunStatusDot from "@components/runs/RunStatusDot";
import Search from "@components/ui/Search";
import { formatRunDateTime, runName } from "@utils/calendar";
import type { RunRow } from "@utils/runRows";
import { searchRuns } from "@utils/runSearch";
import { cx } from "@utils/classNames";
import styles from "./RunSearch.module.css";

// Matches offered; the list shows about five and scrolls for the rest.
const MAX_RESULTS = 20;

type RunSearchProps = {
  rows: readonly RunRow[];
  onSelect: (row: RunRow) => void;
  className?: string;
};

// Figma "Search" in the Runs top bar: find a run by name and/or date. Shows the top
// matches as a listbox (arrow keys + Enter, or click); ⌘K / Ctrl+K focuses it.
// Shorter than the stock Search (36px, like a Button) to sit lighter in the top bar.
export default function RunSearch({ rows, onSelect, className }: RunSearchProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listId = useId();
  const optionId = (index: number) => `${listId}-option-${index}`;

  // About five fit before the list scrolls (RunSearch.module.css).
  const results = useMemo(() => searchRuns(rows, query, MAX_RESULTS), [rows, query]);
  const showList = open && query.trim() !== "";

  // Keep the highlighted result in view as the arrow keys move past the fifth. Only
  // when the highlight moves, so a wheel-scrolled list isn't pulled back on refetch.
  useEffect(() => {
    if (showList) {
      document.getElementById(`${listId}-option-${active}`)?.scrollIntoView({ block: "nearest" });
    }
  }, [active, listId, showList]);

  useEffect(() => {
    if (showList) document.getElementById(optionId(active))?.scrollIntoView({ block: "nearest" });
  });

  useEffect(() => {
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const choose = (row: RunRow) => {
    onSelect(row);
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setOpen(false);
      return;
    }
    if (!showList || results.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => (index + 1) % results.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => (index - 1 + results.length) % results.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(results[Math.min(active, results.length - 1)]);
    }
  };

  return (
    <div className={cx(styles.container, className)}>
      <Search
        className={styles.field}
        ref={inputRef}
        aria-label="Search runs by name or date"
        placeholder="Search runs by name or date…"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList && results.length > 0 ? optionId(active) : undefined}
        autoComplete="off"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setActive(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        // Delay so a click on a result lands before the list closes.
        onBlur={() => setTimeout(() => setOpen(false), 100)}
        onKeyDown={handleKeyDown}
      />
      {showList && (
        <ul id={listId} role="listbox" aria-label="Matching runs" className={styles.results}>
          {results.length === 0 ? (
            <li className={styles.empty} role="presentation">
              No runs match “{query.trim()}”.
            </li>
          ) : (
            results.map((row, index) => (
              <li
                key={row.runId}
                id={optionId(index)}
                role="option"
                aria-selected={index === active}
                className={cx(styles.option, index === active && styles.active)}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActive(index)}
                onClick={() => choose(row)}
              >
                <RunStatusDot status={row.status} />
                <span className={styles.name} title={row.runId}>
                  {runName(row)}
                </span>
                <span className={styles.time}>{formatRunDateTime(row)}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
