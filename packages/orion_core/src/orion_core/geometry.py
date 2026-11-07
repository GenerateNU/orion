"""Position helpers shared by the pipeline and the backend.

Positions are numpy arrays of local x/y meters (see `to_local_xy`), in time order.
"""

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]

# Mean Earth radius, used to turn latitude/longitude angles into meters.
EARTH_RADIUS_M = 6_371_000.0


def to_local_xy(lat: ArrayLike, lon: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Latitude/longitude in degrees to meters east (x) and north (y) of the first point."""
    lat = np.asarray(lat, dtype=np.float64)
    lon = np.asarray(lon, dtype=np.float64)
    if lat.size == 0:
        return lat, lon
    x = EARTH_RADIUS_M * np.radians(lon - lon[0]) * np.cos(np.radians(lat[0]))
    y = EARTH_RADIUS_M * np.radians(lat - lat[0])
    return x, y


def distance_driven(x: FloatArray, y: FloatArray) -> FloatArray:
    """Total distance driven up to each point, in meters. 0 at the first point."""
    steps_m = np.hypot(np.diff(x), np.diff(y))
    return np.concatenate(([0.0], np.cumsum(steps_m)))[: len(x)]
