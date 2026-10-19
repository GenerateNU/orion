import {
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  parseSearchWith,
  redirect,
  stringifySearchWith,
} from "@tanstack/react-router";
import EmptyState from "@components/EmptyState";
import LoadingState from "@components/LoadingState";
import { validateDashboardSearch } from "@features/dashboard/utils/search";
import RunsView from "@views/RunsView";
import App from "./App";

// Routes, in code (few enough not to need file-based routing):
//   /                        → redirect to /runs
//   /runs                    → RunsView
//   /runs/$runId/dashboard   → DashboardView, selection in ?t=&laps= (utils/search.ts)

const rootRoute = createRootRoute({ component: App });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/runs" });
  },
});

const runsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs",
  component: RunsView,
});

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$runId/dashboard",
  validateSearch: validateDashboardSearch,
  component: lazyRouteComponent(() => import("@features/dashboard/DashboardView")),
});

const routeTree = rootRoute.addChildren([indexRoute, runsRoute, dashboardRoute]);

export const router = createRouter({
  routeTree,
  // Search values stay strings in the URL (each route's validateSearch parses
  // them) and lists are written comma-separated: ?laps=3,7 rather than JSON.
  parseSearch: parseSearchWith((value) => value),
  stringifySearch: stringifySearchWith((value) =>
    Array.isArray(value) ? value.join(",") : JSON.stringify(value),
  ),
  defaultPendingComponent: () => <LoadingState />,
  defaultNotFoundComponent: () => <EmptyState message="Page not found." />,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
