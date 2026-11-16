import { z } from "zod";
import { DateTimeSchema, EpochTimesSchema } from "@schemas/common.schema";

// Mirrors SensorResponse in services/backend/.../schemas/sensor_schema.py:
// one Penelope `data_type` row.
export const SensorResponseSchema = z.object({
  // Penelope `dataTypeName`, e.g. "TPU/GPS/Location"; pass it in SensorDataQuery.sensors.
  name: z.string(),
  unit: z.string().nullable(),
});

export type SensorResponse = z.infer<typeof SensorResponseSchema>;

// Mirrors SensorSeries: one sensor's readings, `values[i]` recorded at `time[i]`.
export const SensorSeriesSchema = z.object({
  // Epoch ms, ascending (parsed from the ISO strings the route sends).
  time: EpochTimesSchema,
  // Penelope's `values[]` per reading, unnamed: TPU/GPS/Location is [lat, lon].
  values: z.array(z.array(z.number().nullable())),
  // Only with `with_lap_percent`: each reading's lap, and how far round the run's
  // ideal lap it was (0-100). Same length as `time`; null where unknown.
  lap_id: z.array(z.number().nullable()).optional(),
  lap_percent: z.array(z.number().nullable()).optional(),
});

// Mirrors SensorDataResponse: raw readings straight from Penelope, not downsampled.
export const SensorDataResponseSchema = z.object({
  run_id: z.string(),
  start: DateTimeSchema,
  end: DateTimeSchema,
  // Keyed by `dataTypeName`; a sensor with no readings in the range is empty.
  series: z.record(z.string(), SensorSeriesSchema),
});

export type SensorSeries = z.infer<typeof SensorSeriesSchema>;
export type SensorDataResponse = z.infer<typeof SensorDataResponseSchema>;

export type SensorDataQuery = {
  sensors: string[];
  start: string;
  end: string;
  // Also return `lap_id` and `lap_percent` per reading (from OrionDB).
  with_lap_percent?: boolean;
};
