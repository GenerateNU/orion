import styles from "./Avatar.module.css";

type AvatarProps = {
  // One or two letters, e.g. "CW".
  initials: string;
  // The person's full name, for screen readers and the hover title.
  name: string;
};

// Figma "Avatar".
export default function Avatar({ initials, name }: AvatarProps) {
  return (
    <span className={styles.avatar} role="img" aria-label={name} title={name}>
      {initials}
    </span>
  );
}
