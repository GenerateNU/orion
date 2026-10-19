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

export type RunListFilters = {
  // Only runs with a pipeline job that succeeded with no error.
  processed?: boolean;
};
