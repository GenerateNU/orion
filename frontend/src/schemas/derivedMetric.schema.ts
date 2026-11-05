import { z } from "zod";

// Mirrors DerivedMetricResponse in services/backend/.../schemas/derived_metric_schema.py.
// A metric's data comes back as a SensorDataResponse keyed by `name`.
export const DerivedMetricResponseSchema = z.object({
  name: z.string(),
  unit: z.string(),
});

export type DerivedMetricResponse = z.infer<typeof DerivedMetricResponseSchema>;

export type DerivedMetricQuery = {
  start: string;
  end: string;
};
