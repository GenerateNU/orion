import { z } from "zod";
import { DateTimeSchema } from "@schemas/common.schema";

// Mirrors PipelineStatus in orion_core/models/orion/pipeline_run_model.py.
export const PipelineStatusSchema = z.enum(["queued", "running", "succeeded", "failed"]);

export type PipelineStatus = z.infer<typeof PipelineStatusSchema>;

// Mirrors PipelineRunResponse in orion_core/schemas/pipeline_run_schema.py.
export const PipelineRunResponseSchema = z.object({
  // Pipeline job id, not the Penelope run id.
  id: z.number().int(),
  run_id: z.string(),
  status: PipelineStatusSchema,
  error: z.string().nullable(),
  queued_at: DateTimeSchema,
});

export type PipelineRunResponse = z.infer<typeof PipelineRunResponseSchema>;

export type PipelineRunCreate = {
  run_id: string;
};

export type PipelineRunFilters = {
  run_id?: string;
  status?: PipelineStatus;
  limit?: number;
};

export const isPipelineActive = (status: PipelineStatus | undefined): boolean =>
  status === "queued" || status === "running";
