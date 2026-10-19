import axios, { isAxiosError } from "axios";
import { ErrorResponseSchema } from "@schemas/error.schema";

export class ApiError extends Error {
  // null when the request never got a response (backend down, proxy error).
  readonly status: number | null;

  constructor(status: number | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// Relative base: the Vite dev server proxies /api to the backend (see vite.config.ts).
const client = axios.create({
  baseURL: "/api/v1",
  headers: { Accept: "application/json" },
});

client.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(toApiError(error)),
);

function toApiError(error: unknown): unknown {
  if (!isAxiosError(error)) return error;
  if (!error.response) return new ApiError(null, "Could not reach the Orion API.");

  const { status, data } = error.response;
  const body = ErrorResponseSchema.safeParse(data);

  // Our NotFoundError always names the resource. A bare 404 means the route itself
  // doesn't exist, e.g. a pipeline stage whose backend isn't built yet.
  if (status === 404 && !(body.success && body.data.resource_type)) {
    const route = `${error.config?.method?.toUpperCase() ?? "GET"} ${error.config?.url ?? ""}`;
    return new ApiError(status, `${route} isn't available on the backend yet.`);
  }

  if (!body.success) return new ApiError(status, `Request failed with status ${status}`);
  const { detail } = body.data;
  return new ApiError(
    status,
    typeof detail === "string" ? detail : detail.map((issue) => issue.msg).join("; "),
  );
}

export default client;
