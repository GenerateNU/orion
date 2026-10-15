import PropTypes from "prop-types";

import Husky from "./Husky.jsx";

// Shown when a request succeeded but returned nothing, so an empty list doesn't look broken.
export default function EmptyState({ message }) {
  return (
    <div className="state state--empty">
      <Husky />
      <p>{message}</p>
    </div>
  );
}

EmptyState.propTypes = {
  message: PropTypes.string.isRequired,
};
