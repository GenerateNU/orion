"""Constants for lap detection. See docs/lap_detection.md, section 12.

The tunable values are untuned starting guesses. They can and should move to
Settings later.
"""

# Mean Earth radius, used to turn latitude/longitude angles into meters.
EARTH_RADIUS_M = 6_371_000.0

# Radius of each remembered point's hitbox, in meters.
HITBOX_RADIUS_M = 3.0
# Minimum time between two points for a revisit to count, in seconds.
MIN_REVISIT_TIME_S = 5.0
# Minimum distance driven between two points for a revisit to count, in meters.
MIN_REVISIT_DISTANCE_M = 50.0
# Pass 1 only looks at every Nth point. Set to 1 to use every point.
PASS1_SAMPLE_EVERY = 5
# Minimum distance between the two neighbors used for a heading, in meters.
MIN_HEADING_SPAN_M = 0.1
# The gate reaches this far on each side of its center, in meters.
GATE_HALF_WIDTH_M = 5.0
# Minimum time between two counted gate crossings, in seconds.
MIN_LAP_TIME_S = 10.0
