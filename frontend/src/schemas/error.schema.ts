import { z } from "zod";

// Mirrors schemas/error_schema.py. FastAPI's own 422s send `detail` as a list instead.
export const ErrorResponseSchema = z.object({
  detail: z.union([z.string(), z.array(z.object({ msg: z.string() }).loose())]),
  resource_type: z.string().nullish(),
  resource_id: z.string().nullish(),
});

export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
