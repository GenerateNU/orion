import type { UseQueryOptions } from "@tanstack/react-query";

// The query options a data hook lets its caller set, e.g. `select` to reshape the
// response or `placeholderData: keepPreviousData` to keep the last window on screen.
export type DataQueryOptions<TQueryFnData, TData = TQueryFnData> = Pick<
  UseQueryOptions<TQueryFnData, Error, TData>,
  "select" | "placeholderData" | "enabled"
>;
