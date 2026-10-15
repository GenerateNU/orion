import PropTypes from "prop-types";

import { runLabel } from "../utils/runLabel";

// One clickable row in the run list. Clicking it hands the run back up to whoever renders the list.
// `position` is its place in the list (1 = most recent), shown like a race standing.
export default function RunListItem({ run, position, onSelect }) {
  return (
    <li>
      <button type="button" className="run-card" onClick={() => onSelect(run)}>
        {position && <span className="run-card__position">P{position}</span>}
        <span className="run-card__label">{runLabel(run)}</span>
        {run.dates && <span className="run-card__date">{run.dates}</span>}
        <span className="run-card__arrow" aria-hidden="true">›</span>
      </button>
    </li>
  );
}

RunListItem.propTypes = {
  run: PropTypes.shape({
    run_id: PropTypes.string.isRequired,
    dates: PropTypes.string,
  }).isRequired,
  position: PropTypes.number,
  onSelect: PropTypes.func.isRequired,
};
