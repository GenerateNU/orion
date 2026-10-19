import { cx } from "@utils/classNames";
import styles from "./Pagination.module.css";

type PaginationProps = {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  // Accessible name of the <nav>; give each pagination on a page its own.
  label?: string;
};

type PageSlot = number | "gap-start" | "gap-end";

function pageSlots(page: number, pageCount: number): PageSlot[] {
  if (pageCount <= 7) return Array.from({ length: pageCount }, (_, i) => i + 1);

  const start = Math.max(2, page - 1);
  const end = Math.min(pageCount - 1, page + 1);
  const slots: PageSlot[] = [1];
  if (start > 2) slots.push("gap-start");
  for (let p = start; p <= end; p++) slots.push(p);
  if (end < pageCount - 1) slots.push("gap-end");
  slots.push(pageCount);
  return slots;
}

export default function Pagination({ page, pageCount, onPageChange, label = "Pagination" }: PaginationProps) {
  if (pageCount <= 1) return null;

  return (
    <nav className={styles.pagination} aria-label={label}>
      <button
        type="button"
        className={styles.page}
        aria-label="Previous page"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        ←
      </button>
      {pageSlots(page, pageCount).map((slot) =>
        typeof slot === "number" ? (
          <button
            key={slot}
            type="button"
            className={cx(styles.page, slot === page && styles.current)}
            aria-label={`Page ${slot}`}
            aria-current={slot === page ? "page" : undefined}
            onClick={() => onPageChange(slot)}
          >
            {slot}
          </button>
        ) : (
          <span key={slot} className={styles.gap} aria-hidden="true">
            …
          </span>
        ),
      )}
      <button
        type="button"
        className={styles.page}
        aria-label="Next page"
        disabled={page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      >
        →
      </button>
    </nav>
  );
}
