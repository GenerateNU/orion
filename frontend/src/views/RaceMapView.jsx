import PropTypes from "prop-types";

import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PositionMap from "../components/PositionMap.jsx";
import { usePositionsByBounds } from "../hooks/positional_data";

// Positions come per lap, so for now the map shows one lap of the selected race.
const DEFAULT_LAP = 1;

// Plots the GPS positions for one race from GET /api/races/{id}/laps/{lap}/positions.
export default function RaceMapView({ race, onBack }) {
  const { data: positions, isLoading, error } = usePositionsByBounds(race.race_id, DEFAULT_LAP);

  let content;
  if (isLoading) {
    content = <LoadingState message="Loading GPS data..." />;
  } else if (error) {
    content = <ErrorState title="Couldn't load GPS data" error={error} />;
  } else if (!positions?.length) {
    content = <EmptyState message="No GPS data for this lap." />;
  } else {
    content = <PositionMap positions={positions} />;
  }

  return (
    <section>
      <button type="button" onClick={onBack}>
        ← Back to races
      </button>
      <h2>
        {race.name} <span style={{ color: "#555", fontWeight: "normal" }}>· Lap {DEFAULT_LAP}</span>
      </h2>
      {content}
    </section>
  );
}

RaceMapView.propTypes = {
  race: PropTypes.shape({
    race_id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
  }).isRequired,
  onBack: PropTypes.func.isRequired,
};
