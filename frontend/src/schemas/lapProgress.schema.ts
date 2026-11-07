import { z } from "zod";
import { DateTimeSchema, EpochTimesSchema } from "@schemas/common.schema";

// Mirrors LapProgressResponse in services/backend/.../schemas/lap_progress_schema.py.
export const LapProgressResponseSchema = z.object({
  run_id: z.string(),
  start: DateTimeSchema,
  end: DateTimeSchema,
  // Epoch ms, ascending (parsed from the ISO strings the route sends).
  time: EpochTimesSchema,
  // How far through its lap the car is, from 0 to 1, same length as `time`.
  progress: z.array(z.number()),
  // The lap each point is in, same length as `time`.
  lap_id: z.array(z.number().int()),
});

export type LapProgressResponse = z.infer<typeof LapProgressResponseSchema>;

export type LapProgressQuery = {
  start: string;
  end: string;
};
