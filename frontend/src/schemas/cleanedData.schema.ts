import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// PLANNED: the backend has no cleaned-data route yet. This shape follows the
// existing raw-sensor route (SensorDataResponse), keyed by Orion sensor name
// instead of Penelope tag. Update it when the route is built.
export const CleanedSeriesSchema = z.object({
  time: z.array(DateTimeSchema),
  values: z.array(z.array(z.number().nullable())),
});

export const CleanedDataResponseSchema = z.object({
  run_id: z.string(),
  start: DateTimeSchema,
  end: DateTimeSchema,
  series: z.record(z.string(), CleanedSeriesSchema),
});

export type CleanedDataResponse = z.infer<typeof CleanedDataResponseSchema>;

export type CleanedDataQuery = {
  sensors: string[];
  start: string;
  end: string;
};
