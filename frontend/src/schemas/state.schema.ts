import { z } from "zod";
import { DateTimeSchema, EpochTimesSchema } from "@schemas/common.schema";

// Mirrors StateDataResponse in services/backend/.../schemas/state_schema.py.
export const StateDataResponseSchema = z.object({
  run_id: z.string(),
  start: DateTimeSchema,
  end: DateTimeSchema,
  // Epoch ms, ascending (parsed from the ISO strings the route sends).
  time: EpochTimesSchema,
  // [latitude, longitude], same length as `time`.
  positions: z.array(z.tuple([z.number(), z.number()])),
  // How far around the ideal lap each position is (0-100), same length as `time`;
  // null off track or when the run has no lap percents.
  lap_percent: z.array(z.number().nullable()),
});

export type StateDataResponse = z.infer<typeof StateDataResponseSchema>;

export type StateDataQuery = {
  start: string;
  end: string;
};
