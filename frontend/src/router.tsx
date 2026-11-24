import {
  createRootRoute,
  createRoute,
  createRouter,
  lazyRouteComponent,
  parseSearchWith,
  redirect,
  stringifySearchWith,
} from "@tanstack/react-router";
import EmptyState from "@components/ui/EmptyState";
import LoadingState from "@components/ui/LoadingState";
import { validateDashboardSearch } from "@features/dashboard/utils/search";
import { validateRunsSearch } from "@utils/runsSearchParams";
import RunsView from "@views/RunsView";
import App from "./App";

// Routes, in code (few enough not to need file-based routing):
//   /                        → redirect to /runs
//   /runs                    → RunsView, calendar selection in ?month=&day=&run=
//   /runs/$runId/dashboard   → DashboardView, selection in ?t=&laps= (utils/search.ts)
//   /components              → ComponentsView, dev builds only (components/ui gallery)

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
  validateSearch: validateRunsSearch,
  component: RunsView,
});

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$runId/dashboard",
  validateSearch: validateDashboardSearch,
  component: lazyRouteComponent(() => import("@features/dashboard/DashboardView")),
});

const componentsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/components",
  component: lazyRouteComponent(() => import("@views/ComponentsView")),
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  runsRoute,
  dashboardRoute,
  ...(import.meta.env.DEV ? [componentsRoute] : []),
]);

export const router = createRouter({
  routeTree,
  // Pages scroll inside <main>, not the window, so reset that on navigation.
  scrollToTopSelectors: ["main"],
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
