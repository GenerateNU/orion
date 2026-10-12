import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RunListView from "./RunListView.jsx";
import RunMapView from "./RunMapView.jsx";
import { useRuns } from "../hooks/all_runs";
import { usePositionsByBounds } from "../hooks/positional_data";

vi.mock("../hooks/all_runs", () => ({ useRuns: vi.fn() }));
vi.mock("../hooks/positional_data", () => ({ usePositionsByBounds: vi.fn() }));
// RaceTrack has its own tests; here it just reports what it was given.
vi.mock("../components/RaceTrack.jsx", () => ({
  default: ({ positions }) => <div data-testid="map">{positions.length} points</div>,
}));

const run = { run_id: "11111111-1111-1111-1111-111111111111", dates: "2026-05-14" };
const hookState = (overrides) => ({ data: null, isLoading: false, error: null, ...overrides });

describe("RunListView", () => {
  it("shows a loading indicator while runs load", () => {
    useRuns.mockReturnValue(hookState({ isLoading: true }));
    render(<RunListView onSelectRun={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading runs...");
  });

  it("shows a readable error when the request fails", () => {
    useRuns.mockReturnValue(hookState({ error: new Error("API request failed: 500") }));
    render(<RunListView onSelectRun={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load runs");
  });

  it("says so when there are no runs", () => {
    useRuns.mockReturnValue(hookState({ data: [] }));
    render(<RunListView onSelectRun={() => {}} />);
    expect(screen.getByText("No runs found.")).toBeInTheDocument();
  });

  it("lists runs and reports which one was picked", () => {
    const onSelectRun = vi.fn();
    const other = { run_id: "22222222-2222-2222-2222-222222222222", dates: "2026-06-01" };
    useRuns.mockReturnValue(hookState({ data: [run, other] }));
    render(<RunListView onSelectRun={onSelectRun} />);

    fireEvent.click(screen.getByRole("button", { name: /Run 22222222/ }));
    expect(onSelectRun).toHaveBeenCalledWith(other);
  });
});

describe("RunMapView", () => {
  beforeEach(() => usePositionsByBounds.mockReset());

  it("asks for lap 1 of the selected run", () => {
    usePositionsByBounds.mockReturnValue(hookState({ isLoading: true }));
    render(<RunMapView run={run} onBack={() => {}} />);
    expect(usePositionsByBounds).toHaveBeenCalledWith("11111111-1111-1111-1111-111111111111", 1);
  });

  it("shows a loading indicator while positions load", () => {
    usePositionsByBounds.mockReturnValue(hookState({ isLoading: true }));
    render(<RunMapView run={run} onBack={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading GPS data...");
  });

  it("shows a readable error when the request fails", () => {
    usePositionsByBounds.mockReturnValue(hookState({ error: new TypeError("Failed to fetch") }));
    render(<RunMapView run={run} onBack={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/couldn't reach the server/i);
  });

  it("says so when the lap has no GPS data", () => {
    usePositionsByBounds.mockReturnValue(hookState({ data: [] }));
    render(<RunMapView run={run} onBack={() => {}} />);
    expect(screen.getByText("No GPS data for this lap.")).toBeInTheDocument();
  });

  it("draws the track with the returned positions", () => {
    usePositionsByBounds.mockReturnValue(
      hookState({ data: [{ latitude: 1, longitude: 2 }, { latitude: 3, longitude: 4 }] })
    );
    render(<RunMapView run={run} onBack={() => {}} />);
    expect(screen.getByTestId("map")).toHaveTextContent("2 points");
    expect(screen.getByRole("heading")).toHaveTextContent("Run 11111111");
  });

  it("goes back when the back button is clicked", () => {
    const onBack = vi.fn();
    usePositionsByBounds.mockReturnValue(hookState({ data: [] }));
    render(<RunMapView run={run} onBack={onBack} />);
    fireEvent.click(screen.getByRole("button", { name: /back to runs/i }));
    expect(onBack).toHaveBeenCalled();
  });
});
