import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// Mirrors RunResponse in services/backend/.../schemas/run_schema.py.
export const RunResponseSchema = z.object({
  run_id: z.string(),
  start_time: DateTimeSchema.nullable(),
  end_time: DateTimeSchema.nullable(),
  created_at: DateTimeSchema,
  duration_s: z.number().nullable(),
  // Penelope run.time as stored by the last POST /runs/sync; null until synced.
  run_time: DateTimeSchema.nullable(),
  // A pipeline job succeeded with no error, so the dashboard can be opened.
  processed: z.boolean(),
});

export type RunResponse = z.infer<typeof RunResponseSchema>;

export type RunListFilters = {
  // Only runs with a pipeline job that succeeded with no error.
  processed?: boolean;
};
