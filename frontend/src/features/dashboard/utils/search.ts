import type { TimeWindow } from "@features/dashboard/utils/time";

// The dashboard's search params: the selection that survives a refresh and can be
// shared as a link. Both are lists, written comma-separated (router.tsx):
// ?t=120000,240000&laps=3,7
export type DashboardSearch = {
  // Committed time window in RunTime ms; absent means the whole run.
  t?: TimeWindow;
  // Selected lap ids, ascending.
  laps?: number[];
};

// Values arrive as strings from the URL, or as arrays from navigate().
const toNumbers = (value: unknown): number[] => {
  const parts = Array.isArray(value) ? value : typeof value === "string" ? value.split(",") : [value];
  return parts.map(Number).filter(Number.isFinite);
};

function parseWindow(value: unknown): TimeWindow | undefined {
  if (value === undefined) return undefined;
  const [start, end, ...rest] = toNumbers(value);
  if (start === undefined || end === undefined || rest.length > 0 || start < 0 || end <= start) return undefined;
  return [start, end];
}

function parseLaps(value: unknown): number[] | undefined {
  if (value === undefined) return undefined;
  const laps = [...new Set(toNumbers(value).filter(Number.isInteger))].sort((a, b) => a - b);
  return laps.length > 0 ? laps : undefined;
}

// A malformed param is dropped rather than failing the route: a hand-edited URL
// still opens the run.
export function validateDashboardSearch(search: Record<string, unknown>): DashboardSearch {
  return { t: parseWindow(search.t), laps: parseLaps(search.laps) };
}
