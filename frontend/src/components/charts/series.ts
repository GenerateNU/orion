// Chart series slots, in order: each has a --data-series-N color token in global.css.
export type Series = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export const seriesColor = (series: Series) => `var(--data-series-${series})`;
