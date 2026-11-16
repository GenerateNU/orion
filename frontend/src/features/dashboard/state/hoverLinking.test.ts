import { describe, expect, it, vi } from "vitest";
import { createDashboardStore } from "./dashboardStore";
import { lapAt, type Lap } from "@features/dashboard/utils/laps";

// Graphs and the track map share one hover time: whichever is hovered sets it,
// and every subscriber (each chart's cursor, the track marker) gets it.
describe("shared hover time", () => {
  it("reaches subscribers when set, and when cleared", () => {
    const store = createDashboardStore();
    const seen: (number | null)[] = [];
    store.subscribe((state, previous) => {
      if (state.hoverTime !== previous.hoverTime) seen.push(state.hoverTime);
    });

    store.getState().setHoverTime(12_000);
    store.getState().setHoverTime(12_000);
    store.getState().setHoverTime(null);
    expect(seen).toEqual([12_000, null]);
  });

  it("keeps hover separate per run", () => {
    const a = createDashboardStore();
    const b = createDashboardStore();
    const listener = vi.fn();
    b.subscribe(listener);
    a.getState().setHoverTime(5_000);
    expect(listener).not.toHaveBeenCalled();
  });
});

describe("hovered lap", () => {
  const laps: Lap[] = [
    { id: 1, window: [0, 60_000] },
    { id: 2, window: [60_001, 120_000] },
  ];

  it("is the lap whose span holds the hovered time", () => {
    expect(lapAt(laps, 30_000)).toBe(1);
    expect(lapAt(laps, 90_000)).toBe(2);
    expect(lapAt(laps, 200_000)).toBeNull();
  });
});
