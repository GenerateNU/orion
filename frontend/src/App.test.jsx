import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

vi.mock("./hooks/all_runs", () => ({
  useRuns: () => ({
    data: [{ run_id: "run-1", name: "Test Run", dates: "2026-05-14" }],
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
  it("starts on the run list", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Runs" })).toBeInTheDocument();
    expect(screen.queryByTestId("map")).not.toBeInTheDocument();
  });

  it("opens a run's map from the list and goes back", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Test Run/ }));
    expect(screen.getByTestId("map")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Runs" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back to runs/i }));
    expect(screen.getByRole("heading", { name: "Runs" })).toBeInTheDocument();
  });
});
