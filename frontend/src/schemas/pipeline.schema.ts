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
  // The one step this job runs; null for the whole pipeline.
  step: z.string().nullable(),
  status: PipelineStatusSchema,
  error: z.string().nullable(),
  queued_at: DateTimeSchema,
});

export type PipelineRunResponse = z.infer<typeof PipelineRunResponseSchema>;

// The pipeline's steps, in the order they run. Mirrors the step names registered
// in orion_pipeline/steps.
export const PIPELINE_STEPS = ["clean_step", "state_step", "lap_step"] as const;

export type PipelineStep = (typeof PIPELINE_STEPS)[number];

export type PipelineRunCreate = {
  run_id: string;
  // Run only this step; omit to run the whole pipeline.
  step?: PipelineStep;
};

export type PipelineRunFilters = {
  run_id?: string;
  status?: PipelineStatus;
  limit?: number;
};

export const isPipelineActive = (status: PipelineStatus | undefined): boolean =>
  status === "queued" || status === "running";
