import PropTypes from "prop-types";

import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import RaceTrack from "../components/RaceTrack.jsx";
import { usePositionsByBounds } from "../hooks/positional_data";
import { runLabel } from "../utils/runLabel";

// Positions come per lap, so for now the track shows one lap of the selected run.
const DEFAULT_LAP = 1;

// Draws the GPS positions for one run from GET /api/runs/{id}/laps/{lap}/positions as a track.
export default function RunMapView({ run, onBack }) {
  const { data: positions, isLoading, error } = usePositionsByBounds(run.run_id, DEFAULT_LAP);

  let content;
  if (isLoading) {
    content = <LoadingState message="Loading GPS data..." />;
  } else if (error) {
    content = <ErrorState title="Couldn't load GPS data" error={error} />;
  } else if (!positions?.length) {
    content = <EmptyState message="No GPS data for this lap." />;
  } else {
    content = <RaceTrack positions={positions} />;
  }

  return (
    <section>
      <button type="button" className="back-button" onClick={onBack}>
        ‹ Back to runs
      </button>
      <h2 className="section-title">
        {runLabel(run)} <span className="lap-chip">Lap {DEFAULT_LAP}</span>
      </h2>
      {content}
    </section>
  );
}

RunMapView.propTypes = {
  run: PropTypes.shape({
    run_id: PropTypes.string.isRequired,
  }).isRequired,
  onBack: PropTypes.func.isRequired,
};
