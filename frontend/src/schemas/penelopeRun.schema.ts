import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// Mirrors PenelopeRunResponse in services/backend/.../schemas/penelope_run_schema.py.
export const PenelopeRunResponseSchema = z.object({
  // Penelope run.id (uuid): shown to the user and sent to the API.
  run_id: z.string(),
  time: DateTimeSchema.nullable(),
  processed: z.boolean(),
});

export type PenelopeRunResponse = z.infer<typeof PenelopeRunResponseSchema>;
