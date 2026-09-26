import PropTypes from "prop-types";

import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import RaceListItem from "../components/RaceListItem.jsx";
import { useRaces } from "../hooks/all_races";

// Lists every race from GET /api/races. Picking one hands it up to App, which opens its map.
export default function RaceListView({ onSelectRace }) {
  const { data: races, isLoading, error } = useRaces();

  let content;
  if (isLoading) {
    content = <LoadingState message="Loading races..." />;
  } else if (error) {
    content = <ErrorState title="Couldn't load races" error={error} />;
  } else if (!races?.length) {
    content = <EmptyState message="No races found." />;
  } else {
    content = (
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {races.map((race) => (
          <RaceListItem key={race.race_id} race={race} onSelect={onSelectRace} />
        ))}
      </ul>
    );
  }

  return (
    <section>
      <h2>Races</h2>
      {content}
    </section>
  );
}

RaceListView.propTypes = {
  onSelectRace: PropTypes.func.isRequired,
};
