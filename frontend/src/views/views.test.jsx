import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RaceListView from "./RaceListView.jsx";
import RaceMapView from "./RaceMapView.jsx";
import { useRaces } from "../hooks/all_races";
import { usePositionsByBounds } from "../hooks/positional_data";

vi.mock("../hooks/all_races", () => ({ useRaces: vi.fn() }));
vi.mock("../hooks/positional_data", () => ({ usePositionsByBounds: vi.fn() }));
// Leaflet can't render in jsdom; PositionMap has its own tests.
vi.mock("../components/PositionMap.jsx", () => ({
  default: ({ positions }) => <div data-testid="map">{positions.length} points</div>,
}));

const race = { race_id: 1, name: "Test Race", dates: "2026-05-14" };
const hookState = (overrides) => ({ data: null, isLoading: false, error: null, ...overrides });

describe("RaceListView", () => {
  it("shows a loading indicator while races load", () => {
    useRaces.mockReturnValue(hookState({ isLoading: true }));
    render(<RaceListView onSelectRace={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading races...");
  });

  it("shows a readable error when the request fails", () => {
    useRaces.mockReturnValue(hookState({ error: new Error("API request failed: 500") }));
    render(<RaceListView onSelectRace={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Couldn't load races");
  });

  it("says so when there are no races", () => {
    useRaces.mockReturnValue(hookState({ data: [] }));
    render(<RaceListView onSelectRace={() => {}} />);
    expect(screen.getByText("No races found.")).toBeInTheDocument();
  });

  it("lists races and reports which one was picked", () => {
    const onSelectRace = vi.fn();
    const other = { race_id: 2, name: "Other Race" };
    useRaces.mockReturnValue(hookState({ data: [race, other] }));
    render(<RaceListView onSelectRace={onSelectRace} />);

    fireEvent.click(screen.getByRole("button", { name: /Other Race/ }));
    expect(onSelectRace).toHaveBeenCalledWith(other);
  });
});

describe("RaceMapView", () => {
  beforeEach(() => usePositionsByBounds.mockReset());

  it("asks for lap 1 of the selected race", () => {
    usePositionsByBounds.mockReturnValue(hookState({ isLoading: true }));
    render(<RaceMapView race={race} onBack={() => {}} />);
    expect(usePositionsByBounds).toHaveBeenCalledWith(1, 1);
  });

  it("shows a loading indicator while positions load", () => {
    usePositionsByBounds.mockReturnValue(hookState({ isLoading: true }));
    render(<RaceMapView race={race} onBack={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading GPS data...");
  });

  it("shows a readable error when the request fails", () => {
    usePositionsByBounds.mockReturnValue(hookState({ error: new TypeError("Failed to fetch") }));
    render(<RaceMapView race={race} onBack={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/couldn't reach the server/i);
  });

  it("says so when the lap has no GPS data", () => {
    usePositionsByBounds.mockReturnValue(hookState({ data: [] }));
    render(<RaceMapView race={race} onBack={() => {}} />);
    expect(screen.getByText("No GPS data for this lap.")).toBeInTheDocument();
  });

  it("renders the map with the returned positions", () => {
    usePositionsByBounds.mockReturnValue(
      hookState({ data: [{ latitude: 1, longitude: 2 }, { latitude: 3, longitude: 4 }] })
    );
    render(<RaceMapView race={race} onBack={() => {}} />);
    expect(screen.getByTestId("map")).toHaveTextContent("2 points");
    expect(screen.getByRole("heading")).toHaveTextContent("Test Race");
  });

  it("goes back when the back button is clicked", () => {
    const onBack = vi.fn();
    usePositionsByBounds.mockReturnValue(hookState({ data: [] }));
    render(<RaceMapView race={race} onBack={onBack} />);
    fireEvent.click(screen.getByRole("button", { name: /back to races/i }));
    expect(onBack).toHaveBeenCalled();
  });
});
