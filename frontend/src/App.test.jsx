import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

vi.mock("./hooks/all_races", () => ({
  useRaces: () => ({
    data: [{ race_id: 1, name: "Test Race", dates: "2026-05-14" }],
    isLoading: false,
    error: null,
  }),
}));
vi.mock("./hooks/positional_data", () => ({
  usePositionsByBounds: () => ({
    data: [{ latitude: 42.34, longitude: -71.09 }],
    isLoading: false,
    error: null,
  }),
}));
// Leaflet can't render in jsdom; PositionMap has its own tests.
vi.mock("./components/PositionMap.jsx", () => ({
  default: () => <div data-testid="map" />,
}));

describe("App", () => {
  it("starts on the race list", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Races" })).toBeInTheDocument();
    expect(screen.queryByTestId("map")).not.toBeInTheDocument();
  });

  it("opens a race's map from the list and goes back", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Test Race/ }));
    expect(screen.getByTestId("map")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Races" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back to races/i }));
    expect(screen.getByRole("heading", { name: "Races" })).toBeInTheDocument();
  });
});
