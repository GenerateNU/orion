import PropTypes from "prop-types";

// One clickable row in the run list. Clicking it hands the run back up to whoever renders the list.
export default function RunListItem({ run, onSelect }) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(run)}
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
        <strong>{run.name}</strong>
        {run.dates && <span style={{ color: "#555" }}> · {run.dates}</span>}
      </button>
    </li>
  );
}

RunListItem.propTypes = {
  run: PropTypes.shape({
    run_id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    dates: PropTypes.string,
  }).isRequired,
  onSelect: PropTypes.func.isRequired,
};
