import styles from "@components/State.module.css";

type EmptyStateProps = {
  message: string;
};

export default function EmptyState({ message }: EmptyStateProps) {
  return <p className={styles.state}>{message}</p>;
}
