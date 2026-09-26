import PropTypes from "prop-types";

import { describeError } from "../utils/describeError";

// Shown when a hook returns an error, instead of crashing or rendering a blank screen.
export default function ErrorState({ title = "Something went wrong", error }) {
  return (
    <div role="alert" style={{ color: "#b00020" }}>
      <strong>{title}</strong>
      <p>{describeError(error)}</p>
    </div>
  );
}

ErrorState.propTypes = {
  title: PropTypes.string,
  error: PropTypes.instanceOf(Error),
};
