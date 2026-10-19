import { useState } from "react";
import type { RunResponse } from "@schemas/run.schema";
import { formatRunLabel } from "@utils/format";

type ProcessedRunPickerProps = {
  runs: RunResponse[];
  currentRunId: string | null;
  onLoad: (run: RunResponse) => void;
};

// Date from Penelope; without Penelope, fall back to the run's first reading.
const labelFor = (run: RunResponse) =>
  formatRunLabel({ run_id: run.run_id, time: run.run_time ?? run.start_time });

export default function ProcessedRunPicker({ runs, currentRunId, onLoad }: ProcessedRunPickerProps) {
  const [selectedId, setSelectedId] = useState(currentRunId ?? runs[0]?.run_id ?? "");
  const selected = runs.find((run) => run.run_id === selectedId);

  return (
    <form
      className="picker"
      onSubmit={(event) => {
        event.preventDefault();
        if (selected) onLoad(selected);
      }}
    >
      <label className="field">
        <span className="field__label">Run</span>
        <select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
          {runs.map((run) => (
            <option key={run.run_id} value={run.run_id}>
              {labelFor(run)}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" className="button" disabled={!selected || selected.run_id === currentRunId}>
        {selected && selected.run_id === currentRunId ? "Loaded" : "Load"}
      </button>
    </form>
  );
}
