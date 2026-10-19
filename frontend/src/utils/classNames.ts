// Joins class names, skipping falsy ones: cx(styles.navItem, isActive && styles.active).
export const cx = (...names: Array<string | false | null | undefined>): string =>
  names.filter(Boolean).join(" ");
