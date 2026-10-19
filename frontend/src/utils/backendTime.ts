// Backend timestamps are ISO 8601 strings. OrionDB `runs` and Penelope times carry
// an offset; OrionDB trace tables (estimated_car_state, metrics) are naive UTC, so
// a missing offset is read as UTC. Returns epoch ms, NaN if unparseable.
const HAS_OFFSET = /(?:Z|[+-]\d{2}:?\d{2})$/i;

export function parseBackendTime(iso: string): number {
  return Date.parse(HAS_OFFSET.test(iso) ? iso : `${iso}Z`);
}
