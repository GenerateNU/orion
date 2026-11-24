import { runDate } from "@utils/calendar";
import type { RunRow } from "@utils/runRows";

const pad2 = (n: number) => String(n).padStart(2, "0");
const weekdayFormat = new Intl.DateTimeFormat("en-US", { weekday: "long" });
const monthFormat = new Intl.DateTimeFormat("en-US", { month: "long" });

// Every way a user might type a run's date: "2026-08-15", "8/15/2026", "aug 15",
// "august", "saturday"… Matched by word prefix, so "aug" and "sat" match too.
function dateWords(date: Date): string[] {
  const year = String(date.getFullYear());
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return [
    weekdayFormat.format(date).toLowerCase(),
    monthFormat.format(date).toLowerCase(),
    String(day),
    pad2(day),
    year,
    `${year}-${pad2(month)}-${pad2(day)}`,
    `${month}/${day}/${year}`,
    `${pad2(month)}/${pad2(day)}/${year}`,
    `${month}/${day}`,
    `${pad2(month)}/${pad2(day)}`,
  ];
}

// Higher is better; 0 means the token doesn't match this run at all.
function scoreToken(token: string, runId: string, words: string[]): number {
  if (runId.startsWith(token)) return 4;
  if (runId.includes(token)) return 3;
  if (words.some((word) => word === token)) return 2;
  if (words.some((word) => word.startsWith(token))) return 1;
  return 0;
}

// Top matches for a query by run name (id) and/or date: every word of the query
// must match the id or the date, e.g. "3adaad", "aug 15", "aug 15 3ad", "2026-08-15".
// Best match first, newest first on ties. Runs without a date aren't on the
// calendar, so they aren't offered.
export function searchRuns(rows: readonly RunRow[], query: string, limit = 8): RunRow[] {
  const tokens = query.toLowerCase().replace(/[,.]/g, " ").split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return [];

  const matches: { row: RunRow; score: number; time: number }[] = [];
  for (const row of rows) {
    const date = runDate(row);
    if (!date) continue;
    const runId = row.runId.toLowerCase();
    const words = dateWords(date);
    let score = 0;
    for (const token of tokens) {
      const tokenScore = scoreToken(token, runId, words);
      if (tokenScore === 0) {
        score = 0;
        break;
      }
      score += tokenScore;
    }
    if (score > 0) matches.push({ row, score, time: date.getTime() });
  }

  return matches
    .sort((a, b) => b.score - a.score || b.time - a.time)
    .slice(0, limit)
    .map((match) => match.row);
}
