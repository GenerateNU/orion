import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

// The right pane's graph setup: tabs of graphs, each tab with its own layout. UI
// config, not selection, so it lives here rather than in the URL (only the active
// tab is also in ?view=). One store for the whole app, so every run shows the same
// setup. Persisted to localStorage; kept plain JSON with a schema version so it
// can move to the backend later.

export type GraphLayout = 1 | 2;
// One channel plotted over time; `channel` is a Penelope `dataTypeName`.
export type Graph = { id: string; channel: string };
export type GraphTab = { id: string; name: string; layout: GraphLayout; graphs: Graph[] };

type GraphViewsState = {
  tabs: GraphTab[];
  activeTabId: string;

  addTab: () => void;
  duplicateTab: (tabId: string) => void;
  renameTab: (tabId: string, name: string) => void;
  deleteTab: (tabId: string) => void;
  setActiveTab: (tabId: string) => void;
  setLayout: (tabId: string, layout: GraphLayout) => void;
  addGraph: (tabId: string, channel: string) => void;
  duplicateGraph: (graphId: string) => void;
  setGraphChannel: (graphId: string, channel: string) => void;
  moveGraph: (graphId: string, toTabId: string) => void;
  removeGraph: (graphId: string) => void;
  // Regroups every graph into one tab per sensor.
  groupBySensor: () => void;
};

export const GRAPH_VIEWS_VERSION = 1;

// Not crypto.randomUUID: it's missing outside secure contexts (the dev server on a LAN IP).
const newId = () => Math.random().toString(36).slice(2, 10);

export const DEFAULT_TAB_NAME = "Overview";

const newTab = (name: string, graphs: Graph[] = []): GraphTab => ({
  id: newId(),
  name,
  layout: 1,
  graphs,
});

const copyGraph = (graph: Graph): Graph => ({ ...graph, id: newId() });

// The sensor a channel belongs to: its name without the last segment
// ("TPU/GPS/Location" → "TPU/GPS").
export const sensorOf = (channel: string) =>
  channel.includes("/") ? channel.slice(0, channel.lastIndexOf("/")) : channel;

const mapGraphs = (tabs: GraphTab[], update: (graphs: Graph[], tab: GraphTab) => Graph[]) =>
  tabs.map((tab) => ({ ...tab, graphs: update(tab.graphs, tab) }));

const initialTab = newTab(DEFAULT_TAB_NAME);

export const useGraphViews = create<GraphViewsState>()(
  persist(
    (set) => ({
      tabs: [initialTab],
      activeTabId: initialTab.id,

      addTab: () =>
        set(({ tabs }) => {
          const tab = newTab(`Tab ${tabs.length + 1}`);
          return { tabs: [...tabs, tab], activeTabId: tab.id };
        }),
      // The copy goes right after the original and becomes the active tab.
      duplicateTab: (tabId) =>
        set(({ tabs }) => {
          const index = tabs.findIndex((tab) => tab.id === tabId);
          if (index < 0) return {};
          const source = tabs[index];
          const copy = {
            ...newTab(`${source.name} copy`, source.graphs.map(copyGraph)),
            layout: source.layout,
          };
          return {
            tabs: [...tabs.slice(0, index + 1), copy, ...tabs.slice(index + 1)],
            activeTabId: copy.id,
          };
        }),
      renameTab: (tabId, name) =>
        set(({ tabs }) => ({
          tabs: tabs.map((tab) => (tab.id === tabId && name.trim() ? { ...tab, name } : tab)),
        })),
      // Deleting the last tab leaves a fresh default one.
      deleteTab: (tabId) =>
        set(({ tabs, activeTabId }) => {
          const rest = tabs.filter((tab) => tab.id !== tabId);
          const remaining = rest.length > 0 ? rest : [newTab(DEFAULT_TAB_NAME)];
          const active = remaining.some((tab) => tab.id === activeTabId)
            ? activeTabId
            : remaining[0].id;
          return { tabs: remaining, activeTabId: active };
        }),
      setActiveTab: (activeTabId) => set({ activeTabId }),
      setLayout: (tabId, layout) =>
        set(({ tabs }) => ({
          tabs: tabs.map((tab) => (tab.id === tabId ? { ...tab, layout } : tab)),
        })),
      addGraph: (tabId, channel) =>
        set(({ tabs }) => ({
          tabs: mapGraphs(tabs, (graphs, tab) =>
            tab.id === tabId ? [...graphs, { id: newId(), channel }] : graphs,
          ),
        })),
      // The copy goes right after the original, in the same tab.
      duplicateGraph: (graphId) =>
        set(({ tabs }) => ({
          tabs: mapGraphs(tabs, (graphs) =>
            graphs.flatMap((graph) => (graph.id === graphId ? [graph, copyGraph(graph)] : [graph])),
          ),
        })),
      setGraphChannel: (graphId, channel) =>
        set(({ tabs }) => ({
          tabs: mapGraphs(tabs, (graphs) =>
            graphs.map((graph) => (graph.id === graphId ? { ...graph, channel } : graph)),
          ),
        })),
      moveGraph: (graphId, toTabId) =>
        set(({ tabs }) => {
          const graph = tabs.flatMap((tab) => tab.graphs).find((g) => g.id === graphId);
          if (!graph) return {};
          return {
            tabs: mapGraphs(tabs, (graphs, tab) => {
              const others = graphs.filter((g) => g.id !== graphId);
              return tab.id === toTabId ? [...others, graph] : others;
            }),
          };
        }),
      removeGraph: (graphId) =>
        set(({ tabs }) => ({
          tabs: mapGraphs(tabs, (graphs) => graphs.filter((g) => g.id !== graphId)),
        })),
      groupBySensor: () =>
        set(({ tabs }) => {
          const bySensor = new Map<string, Graph[]>();
          for (const graph of tabs.flatMap((tab) => tab.graphs)) {
            const sensor = sensorOf(graph.channel);
            bySensor.set(sensor, [...(bySensor.get(sensor) ?? []), graph]);
          }
          if (bySensor.size === 0) return {};
          const grouped = [...bySensor].map(([sensor, graphs]) => newTab(sensor, graphs));
          return { tabs: grouped, activeTabId: grouped[0].id };
        }),
    }),
    {
      name: "orion-graph-views",
      version: GRAPH_VIEWS_VERSION,
      // The global, not window.localStorage, so it also works where there's no window (tests).
      storage: createJSONStorage(() => localStorage),
      partialize: ({ tabs, activeTabId }) => ({ tabs, activeTabId }),
    },
  ),
);
