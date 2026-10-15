import PropTypes from "prop-types";

// Shown while a hook is still waiting on the API.
export default function LoadingState({ message = "Loading..." }) {
  return (
    <p role="status" aria-live="polite" className="state state--loading">
      {message}
    </p>
  );
}

LoadingState.propTypes = {
  message: PropTypes.string,
};
