import PropTypes from "prop-types";

// Shown while a hook is still waiting on the API.
export default function LoadingState({ message = "Loading..." }) {
  return (
    <p role="status" aria-live="polite" style={{ color: "#555" }}>
      {message}
    </p>
  );
}

LoadingState.propTypes = {
  message: PropTypes.string,
};
