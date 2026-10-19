import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { runDataKeys } from "@api/queryKeys";
import { router } from "./router";
import "./styles/global.css";

// No automatic retries: the failures this app sees (404 for an unprocessed run,
// 502/503 with Penelope down) don't fix themselves in seconds, and a retry only
// delays the error state. Users retry by navigating or refreshing.
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

// A processed run's data only changes when the run is reprocessed, which
// invalidates it explicitly (usePipelineRuns.ts), so it is never refetched on its
// own and stays cached while the user moves between runs and windows. Structural
// sharing is off: it would deep-compare traces of hundreds of thousands of points
// to keep references that immutable data never needs.
queryClient.setQueryDefaults(runDataKeys.root, {
  staleTime: Infinity,
  gcTime: 30 * 60_000,
  refetchOnWindowFocus: false,
  structuralSharing: false,
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
