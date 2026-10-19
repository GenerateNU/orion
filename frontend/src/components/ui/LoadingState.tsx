import styles from "./State.module.css";

type LoadingStateProps = {
  message?: string;
};

export default function LoadingState({ message = "Loading…" }: LoadingStateProps) {
  return (
    <p className={styles.state} role="status">
      {message}
    </p>
  );
}
