import { useMemo, useState } from "react";

// Hook for client-side pagination of an in-memory list. The page is clamped so it
// stays valid when the list shrinks (e.g. after a refetch).
export const usePagination = <T>(items: readonly T[], pageSize: number) => {
  const [requestedPage, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const page = Math.min(requestedPage, pageCount);
  const start = (page - 1) * pageSize;

  const pageItems = useMemo(() => items.slice(start, start + pageSize), [items, start, pageSize]);

  return {
    page,
    pageCount,
    pageItems,
    setPage,
    firstItem: pageItems.length === 0 ? 0 : start + 1,
    lastItem: start + pageItems.length,
  };
};
