import { parseBackendTime } from "@utils/backendTime";
import type { RunRow } from "@utils/runRows";

// Calendar days are local dates written "YYYY-MM-DD" (a DayKey) and months "YYYY-MM"
// (a MonthKey), so they sort as strings and can go straight into the URL.
export type DayKey = string;
export type MonthKey = string;

const pad2 = (n: number) => String(n).padStart(2, "0");

export const toDayKey = (date: Date): DayKey =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;

export const toMonthKey = (date: Date): MonthKey =>
  `${date.getFullYear()}-${pad2(date.getMonth() + 1)}`;

export const monthOfDay = (day: DayKey): MonthKey => day.slice(0, 7);

// Midday, so DST changes never push a date onto the neighbouring day.
export function parseDayKey(day: DayKey): Date {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(year, month - 1, date, 12);
}

export function parseMonthKey(month: MonthKey): Date {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1, 12);
}

export function addMonths(month: MonthKey, delta: number): MonthKey {
  const date = parseMonthKey(month);
  date.setMonth(date.getMonth() + delta);
  return toMonthKey(date);
}

export const isDayKey = (value: unknown): value is DayKey =>
  typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);

export const isMonthKey = (value: unknown): value is MonthKey =>
  typeof value === "string" && /^\d{4}-\d{2}$/.test(value);

export type CalendarDay = {
  day: DayKey;
  date: Date;
  // false for the leading/trailing days of the neighbouring months.
  inMonth: boolean;
};

// The month as six Monday-first weeks (Figma "Month grid": always 6 rows).
export function monthGrid(month: MonthKey): CalendarDay[][] {
  const first = parseMonthKey(month);
  // getDay() is Sunday-first; shift so Monday is 0.
  const start = new Date(first);
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7));

  return Array.from({ length: 6 }, (_, week) =>
    Array.from({ length: 7 }, (_, weekday) => {
      const date = new Date(start);
      date.setDate(start.getDate() + week * 7 + weekday);
      return { day: toDayKey(date), date, inMonth: toMonthKey(date) === month };
    }),
  );
}

export const runDate = (row: RunRow): Date | null => {
  if (!row.time) return null;
  const ms = parseBackendTime(row.time);
  return Number.isNaN(ms) ? null : new Date(ms);
};

export const runDayKey = (row: RunRow): DayKey | null => {
  const date = runDate(row);
  return date ? toDayKey(date) : null;
};

// Runs grouped by local day, each day in order of time (earliest first).
// Runs without a usable time can't be placed and are left out.
export function groupRunsByDay(rows: readonly RunRow[]): Map<DayKey, RunRow[]> {
  const byDay = new Map<DayKey, RunRow[]>();
  for (const row of rows) {
    const day = runDayKey(row);
    if (!day) continue;
    const list = byDay.get(day);
    if (list) list.push(row);
    else byDay.set(day, [row]);
  }
  for (const list of byDay.values()) {
    list.sort((a, b) => (runDate(a)?.getTime() ?? 0) - (runDate(b)?.getTime() ?? 0));
  }
  return byDay;
}

const timeFormat = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const dayHeadingFormat = new Intl.DateTimeFormat(undefined, {
  weekday: "long",
  month: "long",
  day: "numeric",
});
const dayLabelFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "full" });
const monthHeadingFormat = new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" });

// "09:48"
export const formatRunTime = (row: RunRow) => {
  const date = runDate(row);
  return date ? timeFormat.format(date) : "—";
};

// "Aug 15, 2026, 09:48"
export const formatRunDateTime = (row: RunRow) => {
  const date = runDate(row);
  return date ? dateTimeFormat.format(date) : "No date";
};

// "Saturday, August 15"
export const formatDayHeading = (day: DayKey) => dayHeadingFormat.format(parseDayKey(day));

// "Saturday, August 15, 2026": a day cell's accessible name.
export const formatDayLabel = (day: DayKey) => dayLabelFormat.format(parseDayKey(day));

// "August 2026"
export const formatMonthHeading = (month: MonthKey) =>
  monthHeadingFormat.format(parseMonthKey(month));

// A run's short name, "Run 3adaad41": the start of its Penelope run.id.
export const runName = (row: RunRow) => `Run ${row.runId.slice(0, 8)}`;
