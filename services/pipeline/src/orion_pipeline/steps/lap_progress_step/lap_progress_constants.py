"""Tunable values for the lap progress step (see docs/ideal_lap.md). Untuned
starting values."""

# Picking the ideal lap.
# A lap with a hole in its data longer than this can't be the ideal lap, in seconds.
MAX_GAP_S = 1.0
# A lap longer than this times the shortest full-data lap is several loops merged
# into one, so it can't be the ideal lap.
MAX_LENGTH_RATIO = 1.25
# Distance between the ideal lap's points, in meters.
PATH_SPACING_M = 1.0

# Matching each position to the ideal lap.
# Points farther than this from the ideal lap are off track, in meters. Also how
# far the fallback gate reaches to each side of the track (see ideal_lap.py).
MAX_OFFTRACK_M = 15.0
# Points heading more than this far from the ideal lap's direction are off track
# (spins, wrong way), in degrees.
MAX_HEADING_DIFF_DEG = 60.0
# Points slower than this get no percentage, in meters per second.
MIN_SPEED_MPS = 1.0
# When matching, a full turn-around in direction counts as this many meters, so
# the far side of a hairpin (driven the other way) never looks closest.
HEADING_WEIGHT_M = 10.0
# A lap's first points within this many meters before the start/finish line read
# 0%, and its last points within this many meters past it read 100%.
GATE_MARGIN_M = 20.0
