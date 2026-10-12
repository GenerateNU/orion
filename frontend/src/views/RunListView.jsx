import PropTypes from "prop-types";

import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import RunListItem from "../components/RunListItem.jsx";
import { useRuns } from "../hooks/all_runs";

// Lists every run from GET /api/runs. Picking one hands it up to App, which opens its map.
export default function RunListView({ onSelectRun }) {
  const { data: runs, isLoading, error } = useRuns();

  let content;
  if (isLoading) {
    content = <LoadingState message="Loading runs..." />;
  } else if (error) {
    content = <ErrorState title="Couldn't load runs" error={error} />;
  } else if (!runs?.length) {
    content = <EmptyState message="No runs found." />;
  } else {
    content = (
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {runs.map((run) => (
          <RunListItem key={run.run_id} run={run} onSelect={onSelectRun} />
        ))}
      </ul>
    );
  }

  return (
    <section>
      <h2>Runs</h2>
      {content}
    </section>
  );
}

RunListView.propTypes = {
  onSelectRun: PropTypes.func.isRequired,
};
