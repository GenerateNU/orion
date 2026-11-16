import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useGraphViews } from "@features/dashboard/state/graphViews";
import SensorChartsPanel from "./SensorChartPanel";

const sensorsResult = vi.hoisted(() => ({
  sensors: undefined as { name: string; unit: string | null }[] | undefined,
}));

vi.mock("@hooks/useSensors", () => ({ useSensors: () => sensorsResult }));
vi.mock("@features/dashboard/state/useDashboard", () => ({
  useGraphView: () => undefined,
  useVisibleWindow: () => null,
  useDashboardActions: () => ({ setGraphView: () => {}, resetWindow: () => {} }),
}));
// Server rendering reads a store's initial state, so render its current one instead.
vi.mock("@features/dashboard/state/graphViews", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@features/dashboard/state/graphViews")>();
  const store = actual.useGraphViews;
  return { ...actual, useGraphViews: Object.assign(() => store.getState(), store) };
});
vi.mock("./SensorChart", () => ({
  default: ({ name }: { name: string }) => <p>chart:{name}</p>,
}));

const initial = useGraphViews.getState();
const activeTab = () => useGraphViews.getState().tabs[0];
const render = () => renderToStaticMarkup(<SensorChartsPanel />);

beforeEach(() => {
  useGraphViews.setState({ tabs: initial.tabs, activeTabId: initial.activeTabId });
  sensorsResult.sensors = [{ name: "BMS/Pack/Voltage", unit: "V" }];
});

describe("SensorChartsPanel", () => {
  it("shows the empty state for a tab with no graphs", () => {
    expect(render()).toContain("No graphs in this tab yet.");
  });

  it("plots a graph whose channel is known", () => {
    useGraphViews.getState().addGraph(activeTab().id, "BMS/Pack/Voltage");
    const html = render();
    expect(html).toContain("chart:BMS/Pack/Voltage");
    expect(html).not.toContain("No graphs in this tab yet.");
  });

  it("shows the missing-channel state for a channel no longer listed", () => {
    useGraphViews.getState().addGraph(activeTab().id, "Old/Channel");
    const html = render();
    expect(html).toMatch(/Channel &quot;Old\/Channel&quot; isn&#x27;t available/);
    expect(html).not.toContain("chart:Old/Channel");
  });

  it("waits for the channel list before calling a channel missing", () => {
    sensorsResult.sensors = undefined;
    useGraphViews.getState().addGraph(activeTab().id, "Old/Channel");
    expect(render()).toContain("chart:Old/Channel");
  });

  it("shows the active tab's layout in the layout picker", () => {
    useGraphViews.getState().setLayout(activeTab().id, 2);
    expect(render()).toMatch(/<option value="2" selected="">2 columns/);
  });
});
