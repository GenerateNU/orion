import { useState } from "react";
import type { PenelopeRunResponse } from "@schemas/penelopeRun.schema";
import { formatRunLabel } from "@utils/format";

type PenelopeRunPickerProps = {
  runs: PenelopeRunResponse[];
  isSubmitting: boolean;
  onProcess: (runId: string) => void;
};

export default function PenelopeRunPicker({ runs, isSubmitting, onProcess }: PenelopeRunPickerProps) {
  const unprocessed = runs.filter((run) => !run.processed);
  const processed = runs.filter((run) => run.processed);

  const [selectedId, setSelectedId] = useState(unprocessed[0]?.run_id ?? runs[0]?.run_id ?? "");
  const selected = runs.find((run) => run.run_id === selectedId);

  return (
    <form
      className="picker"
      onSubmit={(event) => {
        event.preventDefault();
        if (selected) onProcess(selected.run_id);
      }}
    >
      <label className="field">
        <span className="field__label">Penelope run</span>
        <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
          {unprocessed.length > 0 && (
            <optgroup label="Not processed">
              {unprocessed.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {formatRunLabel(run)}
                </option>
              ))}
            </optgroup>
          )}
          {processed.length > 0 && (
            <optgroup label="Already processed">
              {processed.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {formatRunLabel(run)} (processed)
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </label>
      <button type="submit" className="button" disabled={!selected || isSubmitting}>
        {isSubmitting ? "Queuing…" : selected?.processed ? "Process again" : "Process"}
      </button>
      {selected?.processed && (
        <p className="note note--warning">
          This run has already been processed. Processing it again replaces its data.
        </p>
      )}
    </form>
  );
}
