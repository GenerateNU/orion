import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RaceTrack from "./RaceTrack.jsx";
import { projectPositions } from "../utils/trackProjection";

const positions = [
  { latitude: 42.34, longitude: -71.09, speed: 10 },
  { latitude: 42.35, longitude: -71.08, speed: 12 },
  { latitude: 42.36, longitude: -71.07, speed: 14 },
];

describe("projectPositions", () => {
  it("keeps north up and east right", () => {
    const [first, , last] = projectPositions(positions, 1000, 500, 20);
    // the last point is further north (smaller y) and further east (larger x)
    expect(last.y).toBeLessThan(first.y);
    expect(last.x).toBeGreaterThan(first.x);
  });

  it("fits every point inside the padded box", () => {
    for (const { x, y } of projectPositions(positions, 1000, 500, 20)) {
      expect(x).toBeGreaterThanOrEqual(20 - 1e-9);
      expect(x).toBeLessThanOrEqual(980 + 1e-9);
      expect(y).toBeGreaterThanOrEqual(20 - 1e-9);
      expect(y).toBeLessThanOrEqual(480 + 1e-9);
    }
  });

  it("puts a single point in the centre instead of dividing by zero", () => {
    expect(projectPositions([positions[0]], 1000, 500, 20)).toEqual([{ x: 500, y: 250 }]);
  });

  it("returns nothing for no points", () => {
    expect(projectPositions([], 1000, 500)).toEqual([]);
  });
});

describe("RaceTrack", () => {
  it("draws the positions as one line, in order", () => {
    render(<RaceTrack positions={positions} />);
    const d = screen.getByTestId("racing-line").getAttribute("d");
    expect(d.match(/[ML]/g)).toEqual(["M", "L", "L"]);
  });

  it("marks the start and the latest position", () => {
    render(<RaceTrack positions={positions} />);
    expect(screen.getByTestId("start-marker")).toHaveTextContent("START");
    expect(screen.getByTestId("end-marker")).toHaveTextContent("END");
  });

  it("describes itself for screen readers and shows the point count", () => {
    render(<RaceTrack positions={positions} />);
    expect(screen.getByRole("img", { name: /3 GPS points/ })).toBeInTheDocument();
    expect(screen.getByText("3 GPS points")).toBeInTheDocument();
  });

  it("renders a single point without crashing", () => {
    render(<RaceTrack positions={[positions[0]]} />);
    expect(screen.getByTestId("start-marker")).toBeInTheDocument();
  });
});

const timed = [
  { timestamp: "2026-05-14T12:00:00Z", latitude: 42.34, longitude: -71.09 },
  { timestamp: "2026-05-14T12:00:10Z", latitude: 42.35, longitude: -71.08 },
  { timestamp: "2026-05-14T12:00:20Z", latitude: 42.36, longitude: -71.07 },
];

describe("RaceTrack playback", () => {
  const carTransform = () => screen.getByTestId("car").getAttribute("transform");

  it("starts paused at the start line", () => {
    render(<RaceTrack positions={timed} />);
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
    expect(screen.getByTestId("lap-time")).toHaveTextContent("0:00.0");
    expect(screen.getByText("0:00.0 / 0:20.0")).toBeInTheDocument();
  });

  it("toggles between play and pause", () => {
    render(<RaceTrack positions={timed} />);
    fireEvent.click(screen.getByRole("button", { name: "Play" }));
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
  });

  it("moves the car and the clock when scrubbing", () => {
    render(<RaceTrack positions={timed} />);
    const atStart = carTransform();

    fireEvent.change(screen.getByRole("slider", { name: "Lap progress" }), { target: { value: "15" } });

    expect(carTransform()).not.toBe(atStart);
    expect(screen.getByTestId("lap-time")).toHaveTextContent("0:15.0");
  });

  it("shows a speed estimated from the GPS points", () => {
    render(<RaceTrack positions={timed} />);
    // ~1.4 km every 10 s is roughly 500 km/h -- just check a number is shown
    expect(screen.getByText(/^\d+ km\/h$/)).toBeInTheDocument();
  });

  it("lets you pick the playback speed", () => {
    render(<RaceTrack positions={timed} />);
    const tenX = screen.getByRole("button", { name: "10×" });
    fireEvent.click(tenX);
    expect(tenX).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "5×" })).toHaveAttribute("aria-pressed", "false");
  });
});
