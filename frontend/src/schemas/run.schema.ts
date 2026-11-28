import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// Mirrors RunResponse in services/backend/.../schemas/run_schema.py.
export const RunResponseSchema = z.object({
  run_id: z.string(),
  start_time: DateTimeSchema.nullable(),
  end_time: DateTimeSchema.nullable(),
  created_at: DateTimeSchema,
  duration_s: z.number().nullable(),
  // Penelope run.time; null when Penelope is not configured or unreachable.
  run_time: DateTimeSchema.nullable(),
});

export type RunResponse = z.infer<typeof RunResponseSchema>;

// Mirrors RunLapSummaryResponse in services/backend/.../schemas/run_schema.py.
// Before the lap step has run: lap_count 0 and both best-lap fields null.
export const RunLapSummaryResponseSchema = z.object({
  run_id: z.string(),
  lap_count: z.number().int(),
  best_lap_id: z.number().int().nullable(),
  best_lap_time_s: z.number().nullable(),
});

export type RunLapSummaryResponse = z.infer<typeof RunLapSummaryResponseSchema>;

export type RunListFilters = {
  // Only runs with a pipeline job that succeeded with no error.
  processed?: boolean;
};
