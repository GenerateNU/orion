import PropTypes from "prop-types";

// Shown when a request succeeded but returned nothing, so an empty list doesn't look broken.
export default function EmptyState({ message }) {
  return <p style={{ color: "#555" }}>{message}</p>;
}

EmptyState.propTypes = {
  message: PropTypes.string.isRequired,
};
