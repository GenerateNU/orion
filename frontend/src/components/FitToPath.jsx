import PropTypes from "prop-types";
import { useMap } from "react-leaflet"
import { useEffect } from "react";


// MapContainer only reads its bounds once on mount, so this custom component
// re-zooms when the positions change.
export default function FitToPath({ path }) {
  const map = useMap();

  useEffect(() => {
    map.fitBounds(path, { padding: [24, 24], maxZoom: 18 });
  }, [map, path]);

  return null;
}

FitToPath.propTypes = {
  path: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.number)).isRequired,
};