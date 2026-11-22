import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// Mirrors LapResponse in services/backend/.../schemas/lap_schema.py: one lap of a run.
export const LapSchema = z.object({
  lap_id: z.number().int(),
  start_time: DateTimeSchema,
  end_time: DateTimeSchema,
});

// Mirrors LapsResponse: every lap of one run, in order.
export const LapsResponseSchema = z.object({
  run_id: z.string(),
  laps: z.array(LapSchema),
});

export type LapRow = z.infer<typeof LapSchema>;
export type LapsResponse = z.infer<typeof LapsResponseSchema>;
