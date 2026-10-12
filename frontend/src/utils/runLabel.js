// Runs have no name (the API only knows their UUID and date), so they're labelled
// by the start of their UUID -- enough to tell runs on the same day apart.

export function runLabel(run) {
  return `Run ${run.run_id.slice(0, 8)}`;
}
