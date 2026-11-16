import { beforeEach, describe, expect, it } from "vitest";
import { GRAPH_VIEWS_VERSION, sensorOf, useGraphViews } from "./graphViews";

// localStorage is the in-memory one from src/test/setup.ts.
const KEY = "orion-graph-views";

const initial = useGraphViews.getState();
const state = () => useGraphViews.getState();
const tab = (index = 0) => state().tabs[index];

beforeEach(() => {
  useGraphViews.setState({ tabs: initial.tabs, activeTabId: initial.activeTabId });
  localStorage.clear();
});

describe("graphs", () => {
  it("adds, edits, moves and removes graphs", () => {
    state().addGraph(tab().id, "BMS/Pack/Voltage");
    const graph = tab().graphs[0];
    expect(graph.channel).toBe("BMS/Pack/Voltage");

    state().setGraphChannel(graph.id, "BMS/Pack/Current");
    expect(tab().graphs).toEqual([{ id: graph.id, channel: "BMS/Pack/Current" }]);

    state().addTab();
    state().moveGraph(graph.id, tab(1).id);
    expect(tab(0).graphs).toEqual([]);
    expect(tab(1).graphs.map((g) => g.id)).toEqual([graph.id]);

    state().removeGraph(graph.id);
    expect(tab(1).graphs).toEqual([]);
  });

  it("duplicates a graph right after the original", () => {
    state().addGraph(tab().id, "BMS/Pack/Voltage");
    state().addGraph(tab().id, "TPU/GPS/Location");
    const [first] = tab().graphs;
    state().duplicateGraph(first.id);
    const channels = tab().graphs.map((g) => g.channel);
    expect(channels).toEqual(["BMS/Pack/Voltage", "BMS/Pack/Voltage", "TPU/GPS/Location"]);
    expect(tab().graphs[1].id).not.toBe(first.id);
  });
});

describe("layouts", () => {
  it("switches the layout of one tab only", () => {
    state().addTab();
    state().setLayout(tab(1).id, 2);
    expect(tab(0).layout).toBe(1);
    expect(tab(1).layout).toBe(2);
  });
});

describe("tabs", () => {
  it("creates, renames and deletes tabs", () => {
    state().addTab();
    expect(state().tabs).toHaveLength(2);
    expect(state().activeTabId).toBe(tab(1).id);

    state().renameTab(tab(1).id, "Battery");
    expect(tab(1).name).toBe("Battery");
    state().renameTab(tab(1).id, "  ");
    expect(tab(1).name).toBe("Battery");

    state().deleteTab(tab(1).id);
    expect(state().tabs.map((t) => t.name)).toEqual(["Overview"]);
    expect(state().activeTabId).toBe(tab(0).id);
  });

  it("duplicates a tab with its graphs and layout, and opens the copy", () => {
    state().addGraph(tab().id, "BMS/Pack/Voltage");
    state().setLayout(tab().id, 2);
    state().duplicateTab(tab().id);

    expect(state().tabs.map((t) => t.name)).toEqual(["Overview", "Overview copy"]);
    expect(tab(1)).toMatchObject({ layout: 2, graphs: [{ channel: "BMS/Pack/Voltage" }] });
    expect(tab(1).graphs[0].id).not.toBe(tab(0).graphs[0].id);
    expect(state().activeTabId).toBe(tab(1).id);
  });

  it("resets to a default tab when the last one is deleted", () => {
    state().addGraph(tab().id, "BMS/Pack/Voltage");
    const only = tab().id;
    state().deleteTab(only);
    expect(state().tabs).toHaveLength(1);
    expect(tab()).toMatchObject({ name: "Overview", layout: 1, graphs: [] });
    expect(tab().id).not.toBe(only);
    expect(state().activeTabId).toBe(tab().id);
  });
});

describe("group by sensor", () => {
  it("uses the channel name without its last segment as the sensor", () => {
    expect(sensorOf("TPU/GPS/Location")).toBe("TPU/GPS");
    expect(sensorOf("Speed")).toBe("Speed");
  });

  it("makes one tab per sensor holding its graphs", () => {
    state().addGraph(tab().id, "BMS/Pack/Voltage");
    state().addTab();
    state().addGraph(tab(1).id, "TPU/GPS/Location");
    state().addGraph(tab(1).id, "BMS/Pack/Current");

    state().groupBySensor();
    expect(
      state().tabs.map((t) => ({ name: t.name, channels: t.graphs.map((g) => g.channel) })),
    ).toEqual([
      { name: "BMS/Pack", channels: ["BMS/Pack/Voltage", "BMS/Pack/Current"] },
      { name: "TPU/GPS", channels: ["TPU/GPS/Location"] },
    ]);
    expect(state().activeTabId).toBe(tab(0).id);
  });

  it("leaves the tabs alone when there are no graphs", () => {
    const before = state().tabs;
    state().groupBySensor();
    expect(state().tabs).toBe(before);
  });
});

describe("persistence", () => {
  it("saves tabs, graphs, layouts and the active tab with a schema version", () => {
    state().addGraph(tab().id, "BMS/Pack/Voltage");
    state().setLayout(tab().id, 2);

    const saved = JSON.parse(localStorage.getItem(KEY)!);
    expect(saved.version).toBe(GRAPH_VIEWS_VERSION);
    expect(saved.state).toEqual({ tabs: state().tabs, activeTabId: state().activeTabId });
  });

  it("restores a saved setup", async () => {
    const tabs = [
      { id: "a", name: "Battery", layout: 2, graphs: [{ id: "g1", channel: "BMS/Pack/Voltage" }] },
      { id: "b", name: "GPS", layout: 1, graphs: [] },
    ];
    localStorage.setItem(
      KEY,
      JSON.stringify({ state: { tabs, activeTabId: "b" }, version: GRAPH_VIEWS_VERSION }),
    );

    await useGraphViews.persist.rehydrate();
    expect(state().tabs).toEqual(tabs);
    expect(state().activeTabId).toBe("b");
  });
});
