import { ApiError } from "@api/client";

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.status === null ? error.message : `${error.message} (HTTP ${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}
