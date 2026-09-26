import PropTypes from "prop-types";
import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// MapContainer only reads its bounds once on mount, so this re-zooms when the positions change.
function FitToPath({ path }) {
  const map = useMap();

  useEffect(() => {
    map.fitBounds(path, { padding: [24, 24], maxZoom: 18 });
  }, [map, path]);

  return null;
}

FitToPath.propTypes = {
  path: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.number)).isRequired,
};

// Draws a lap's GPS positions as a line, with the start and end points marked.
// Expects positions shaped like the /positions endpoint: [{ latitude, longitude, ... }].
export default function PositionMap({ positions, height = "500px" }) {
  const path = positions.map((p) => [p.latitude, p.longitude]);
  const start = path[0];
  const end = path[path.length - 1];

  return (
    <MapContainer bounds={path} style={{ height, width: "100%" }} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Polyline positions={path} pathOptions={{ color: "#2563eb", weight: 4 }} />
      <CircleMarker center={start} radius={7} pathOptions={{ color: "#16a34a", fillOpacity: 1 }}>
        <Tooltip>Start</Tooltip>
      </CircleMarker>
      <CircleMarker center={end} radius={7} pathOptions={{ color: "#dc2626", fillOpacity: 1 }}>
        <Tooltip>End</Tooltip>
      </CircleMarker>
      <FitToPath path={path} />
    </MapContainer>
  );
}

PositionMap.propTypes = {
  positions: PropTypes.arrayOf(
    PropTypes.shape({
      latitude: PropTypes.number.isRequired,
      longitude: PropTypes.number.isRequired,
    })
  ).isRequired,
  height: PropTypes.string,
};
