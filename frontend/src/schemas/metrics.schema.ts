import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// GET /runs/{run_id}/metrics: one entry per lap of the `metrics` table. Which
// per-lap metrics to add is still open (docs/ARCHITECTURE.md).
export const LapMetricsSchema = z.object({
  lap_number: z.number().int(),
  start_time: DateTimeSchema,
  end_time: DateTimeSchema,
});

export const MetricsResponseSchema = z.object({
  run_id: z.string(),
  laps: z.array(LapMetricsSchema),
});

export type LapMetrics = z.infer<typeof LapMetricsSchema>;
export type MetricsResponse = z.infer<typeof MetricsResponseSchema>;
