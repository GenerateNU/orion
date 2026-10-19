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

// "00d5d5a4-b368-4452-b6c7-278311190931 · Jul 11, 2026". The id is Penelope's
// run.id, which every part of Orion uses (Penelope's numeric runId isn't unique).
export function formatRunLabel(run: { run_id: string; time: string | null }): string {
  return run.time ? `${run.run_id} · ${formatDate(run.time)}` : run.run_id;
}
