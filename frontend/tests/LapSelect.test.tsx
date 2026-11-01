import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LapSelect from "@features/dashboard/components/LapSelect";
import { useLaps } from "@features/dashboard/data/useDashboardData";
import {
  useDashboardActions,
  useDashboardRun,
  useSelectedLaps,
} from "@features/dashboard/state/useDashboard";
import type { Lap } from "@features/dashboard/utils/laps";

// The dropdown is tested on its own: the hooks it reads are replaced, and each
// test says what they return.
vi.mock("@features/dashboard/data/useDashboardData", () => ({ useLaps: vi.fn() }));
vi.mock("@features/dashboard/state/useDashboard", () => ({
  useDashboardActions: vi.fn(),
  useDashboardRun: vi.fn(),
  useSelectedLaps: vi.fn(),
}));

const LAPS: Lap[] = [
  { id: 1, window: [0, 60_000] },
  { id: 2, window: [60_000, 120_000] },
  { id: 3, window: [120_000, 180_000] },
];

const selectLaps = vi.fn();
const setHoverLap = vi.fn();

type Setup = {
  laps?: Lap[] | undefined;
  selected?: number[];
  isLoading?: boolean;
  error?: Error | null;
  hasTimeline?: boolean;
};

function setup({
  laps = LAPS,
  selected = [],
  isLoading = false,
  error = null,
  hasTimeline = true,
}: Setup = {}) {
  vi.mocked(useDashboardRun).mockReturnValue({
    timeline: hasTimeline ? { startMs: 0, durationMs: 180_000 } : null,
  } as ReturnType<typeof useDashboardRun>);
  vi.mocked(useLaps).mockReturnValue({ laps, lapsIsLoading: isLoading, lapsError: error });
  vi.mocked(useSelectedLaps).mockReturnValue(selected);
  vi.mocked(useDashboardActions).mockReturnValue({
    selectLaps,
    setHoverLap,
  } as unknown as ReturnType<typeof useDashboardActions>);
  render(<LapSelect />);
}

const user = userEvent.setup();
// The dropdown button (the only one with aria-expanded), while closed.
const trigger = () => screen.getByRole("button", { expanded: false });
const lapBox = (id: number) => screen.getByRole("checkbox", { name: new RegExp(`^Lap ${id}\\b`) });
const selectAll = () => screen.getByRole("checkbox", { name: "Select all" });

beforeEach(() => vi.clearAllMocks());

describe("LapSelect: choosing laps", () => {
  it("lists every lap when opened", async () => {
    setup();
    await user.click(trigger());
    for (const lap of LAPS) expect(lapBox(lap.id)).toBeInTheDocument();
  });

  it("adds a ticked lap to the selection", async () => {
    setup({ selected: [2] });
    await user.click(trigger());
    await user.click(lapBox(3));
    expect(selectLaps).toHaveBeenCalledWith([2, 3]);
  });

  it("removes an unticked lap", async () => {
    setup({ selected: [2, 3] });
    await user.click(trigger());
    await user.click(lapBox(2));
    expect(selectLaps).toHaveBeenCalledWith([3]);
  });

  it("Clear empties the selection", async () => {
    setup({ selected: [2] });
    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(selectLaps).toHaveBeenCalledWith([]);
  });

  it("Clear is disabled when nothing is selected", () => {
    setup();
    expect(screen.getByRole("button", { name: "Clear" })).toBeDisabled();
  });

  it("Select all selects every lap", async () => {
    setup({ selected: [2] });
    await user.click(trigger());
    await user.click(selectAll());
    expect(selectLaps).toHaveBeenCalledWith([1, 2, 3]);
  });

  it("Select all clears when every lap is selected", async () => {
    setup({ selected: [1, 2, 3] });
    await user.click(trigger());
    expect(selectAll()).toBeChecked();
    await user.click(selectAll());
    expect(selectLaps).toHaveBeenCalledWith([]);
  });

  it("ignores lap ids the run doesn't have", async () => {
    setup({ selected: [2, 99] });
    await user.click(trigger());
    expect(lapBox(2)).toBeChecked();
    await user.click(lapBox(3));
    expect(selectLaps).toHaveBeenCalledWith([2, 3]);
  });

  it("reports the hovered lap, and none after leaving the list", async () => {
    setup();
    await user.click(trigger());
    await user.hover(lapBox(2).closest("label")!);
    expect(setHoverLap).toHaveBeenLastCalledWith(2);
    await user.unhover(screen.getByRole("group"));
    expect(setHoverLap).toHaveBeenLastCalledWith(null);
  });
});

describe("LapSelect: button text", () => {
  it.each([
    [[], "No laps selected"],
    [[2], "Lap 2"],
    [[2, 3], "Laps 2, 3"],
    [[1, 2, 3], "All laps"],
  ])("selected %j shows %s", (selected, text) => {
    setup({ selected });
    expect(trigger()).toHaveTextContent(text);
  });
});

describe("LapSelect: states", () => {
  it.each<[string, Setup, string]>([
    ["loading", { isLoading: true, laps: undefined }, "Loading laps…"],
    ["error", { error: new Error("boom"), laps: undefined }, "Laps unavailable"],
    ["no laps", { laps: [] }, "No laps detected"],
    ["no run times", { hasTimeline: false, laps: undefined }, "No laps detected"],
  ])("%s: disabled, shows %s", (_name, options, text) => {
    setup(options);
    expect(trigger()).toBeDisabled();
    expect(trigger()).toHaveTextContent(text);
  });
});
