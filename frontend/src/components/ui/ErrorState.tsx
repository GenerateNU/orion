import { describeError } from "@utils/describeError";
import { cx } from "@utils/classNames";
import styles from "./State.module.css";

type ErrorStateProps = {
  error: unknown;
};

export default function ErrorState({ error }: ErrorStateProps) {
  return (
    <p className={cx(styles.state, styles.error)} role="alert">
      {describeError(error)}
    </p>
  );
}
