const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatDate(iso: string | null): string {
  return iso ? dateFormat.format(new Date(iso)) : "—";
}

export function formatDateTime(iso: string | null): string {
  return iso ? dateTimeFormat.format(new Date(iso)) : "—";
}

const pad2 = (n: number) => String(n).padStart(2, "0");

// "06:30" (mm:ss), or "1:02:41" past an hour.
export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = `${pad2(minutes)}:${pad2(total % 60)}`;
  return hours > 0 ? `${hours}:${rest}` : rest;
}

// "00:39.93" (mm:ss.cc): a lap time, to the hundredth. Minutes padded like formatDuration.
export function formatLapTime(seconds: number | null): string {
  if (seconds === null) return "—";
  const hundredths = Math.round(seconds * 100);
  const minutes = Math.floor(hundredths / 6000);
  const rest = (hundredths % 6000) / 100;
  return `${pad2(minutes)}:${rest.toFixed(2).padStart(5, "0")}`;
}

// "00d5d5a4-b368-4452-b6c7-278311190931 · Jul 11, 2026". The id is Penelope's
// run.id, which every part of Orion uses (Penelope's numeric runId isn't unique).
export function formatRunLabel(run: { run_id: string; time: string | null }): string {
  return run.time ? `${run.run_id} · ${formatDate(run.time)}` : run.run_id;
}
