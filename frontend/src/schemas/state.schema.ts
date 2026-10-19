import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// Mirrors StateDataResponse in services/backend/.../schemas/state_schema.py.
export const StateDataResponseSchema = z.object({
  run_id: z.string(),
  start: DateTimeSchema,
  end: DateTimeSchema,
  time: z.array(DateTimeSchema),
  // [latitude, longitude], same length as `time`.
  positions: z.array(z.tuple([z.number(), z.number()])),
});

export type StateDataResponse = z.infer<typeof StateDataResponseSchema>;

export type StateDataQuery = {
  start: string;
  end: string;
};
