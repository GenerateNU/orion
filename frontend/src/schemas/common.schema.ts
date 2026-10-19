import { z } from "zod";
import { parseBackendTime } from "@utils/backendTime";

// The backend sends ISO 8601 strings. OrionDB `runs` / Penelope times carry an
// offset; OrionDB trace tables (estimated_car_state, metrics) are naive, so allow both.
export const DateTimeSchema = z.iso.datetime({ offset: true, local: true });

// A trace's time axis: ISO strings parsed once, during validation, into epoch ms.
// Traces run to hundreds of thousands of points, so this is cheaper to validate
// than DateTimeSchema per string, and a Float64Array takes 8 bytes per point and
// is cached once, shared by every panel that reads it.
export const EpochTimesSchema = z.array(z.string()).transform((times, ctx) => {
  const epochMs = Float64Array.from(times, parseBackendTime);
  const bad = epochMs.findIndex(Number.isNaN);
  if (bad !== -1) {
    ctx.issues.push({
      code: "custom",
      message: `Invalid timestamp at index ${bad}: ${times[bad]}`,
      input: times,
    });
    return z.NEVER;
  }
  return epochMs;
});
