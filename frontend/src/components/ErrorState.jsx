import PropTypes from "prop-types";

import { describeError } from "../utils/describeError";

// Shown when a hook returns an error, instead of crashing or rendering a blank screen.
export default function ErrorState({ title = "Something went wrong", error }) {
  return (
    <div role="alert" className="state state--error">
      <strong>{title}</strong>
      <p>{describeError(error)}</p>
    </div>
  );
}

// Prop type checks for dev
ErrorState.propTypes = {
  title: PropTypes.string,
  error: PropTypes.instanceOf(Error),
};
