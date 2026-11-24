import { isDayKey, isMonthKey, type DayKey, type MonthKey } from "@utils/calendar";

// The Runs calendar's search params, so the selection survives a refresh and the
// browser's back button from a dashboard: ?month=2026-08&day=2026-08-15&run=<run id>
export type RunsSearch = {
  // Month shown; absent means the current month (or the selected day's month).
  month?: MonthKey;
  // Selected day: opens the day panel.
  day?: DayKey;
  // Selected run id within that day.
  run?: string;
};

// A malformed param is dropped rather than failing the route.
export function validateRunsSearch(search: Record<string, unknown>): RunsSearch {
  const day = isDayKey(search.day) ? search.day : undefined;
  return {
    month: isMonthKey(search.month) ? search.month : undefined,
    day,
    run: day && typeof search.run === "string" && search.run ? search.run : undefined,
  };
}
