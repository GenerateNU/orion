import PropTypes from "prop-types";

// One clickable row in the race list. Clicking it hands the race back up to whoever renders the list.
export default function RaceListItem({ race, onSelect }) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(race)}
        style={{
          width: "100%",
          textAlign: "left",
          padding: "0.75rem 1rem",
          marginBottom: "0.5rem",
          border: "1px solid #ddd",
          borderRadius: "6px",
          background: "white",
          cursor: "pointer",
        }}
      >
        <strong>{race.name}</strong>
        {race.dates && <span style={{ color: "#555" }}> · {race.dates}</span>}
      </button>
    </li>
  );
}

RaceListItem.propTypes = {
  race: PropTypes.shape({
    race_id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    dates: PropTypes.string,
  }).isRequired,
  onSelect: PropTypes.func.isRequired,
};
