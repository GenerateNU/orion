/* eslint-disable react/prop-types -- the react-leaflet stand-ins below aren't real components */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PositionMap from "./PositionMap.jsx";

// Leaflet needs real layout (element sizes) that jsdom doesn't have, so swap react-leaflet
// for stand-ins that just record what PositionMap hands them.
const fitBounds = vi.fn();
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  Polyline: ({ positions }) => <div data-testid="path" data-positions={JSON.stringify(positions)} />,
  CircleMarker: ({ center, children }) => (
    <div data-testid="marker" data-center={JSON.stringify(center)}>
      {children}
    </div>
  ),
  Tooltip: ({ children }) => <span>{children}</span>,
  useMap: () => ({ fitBounds }),
}));

const positions = [
  { latitude: 42.34, longitude: -71.09, speed: 10 },
  { latitude: 42.35, longitude: -71.08, speed: 12 },
  { latitude: 42.36, longitude: -71.07, speed: 14 },
];

describe("PositionMap", () => {
  it("draws the positions as one path in order", () => {
    render(<PositionMap positions={positions} />);
    expect(JSON.parse(screen.getByTestId("path").dataset.positions)).toEqual([
      [42.34, -71.09],
      [42.35, -71.08],
      [42.36, -71.07],
    ]);
  });

  it("marks the first point as start and the last as end", () => {
    render(<PositionMap positions={positions} />);
    const [start, end] = screen.getAllByTestId("marker");
    expect(start).toHaveTextContent("Start");
    expect(JSON.parse(start.dataset.center)).toEqual([42.34, -71.09]);
    expect(end).toHaveTextContent("End");
    expect(JSON.parse(end.dataset.center)).toEqual([42.36, -71.07]);
  });

  it("zooms the map to fit the path", () => {
    render(<PositionMap positions={positions} />);
    expect(fitBounds).toHaveBeenCalledWith(
      [
        [42.34, -71.09],
        [42.35, -71.08],
        [42.36, -71.07],
      ],
      expect.any(Object)
    );
  });
});
