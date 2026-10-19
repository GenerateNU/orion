import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// PLANNED: there is no metrics step or route yet, and which metrics to compute is
// still open (docs/ARCHITECTURE.md). This shape follows the `metrics` table
// (one row per lap with its time bounds). Update it when the route is built.
export const LapMetricsSchema = z.object({
  lap_id: z.number().int(),
  start_time: DateTimeSchema,
  end_time: DateTimeSchema,
});

export const MetricsResponseSchema = z.object({
  run_id: z.string(),
  laps: z.array(LapMetricsSchema),
});

export type LapMetrics = z.infer<typeof LapMetricsSchema>;
export type MetricsResponse = z.infer<typeof MetricsResponseSchema>;
