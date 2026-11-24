"""Tunables for the sliding-window GPS lag tracker (`gps_lag.py`).

Every knob lives here so the tracker can be tuned without touching its logic.
Times are seconds, speeds are mph.
"""

from dataclasses import dataclass

# GroundSpeed is logged in m/s; the tracker compares speeds in mph.
MS_TO_MPH = 2.23694
# Fewest moving samples needed to fit the GPS/VCU scale factor.
MIN_FIT_SAMPLES = 30


@dataclass(frozen=True)
class LagTrackerConfig:
    # Candidate delays searched in every window (s). lag > 0 means GPS is late.
    lag_min: float = -5.0
    lag_max: float = 20.0
    lag_step: float = 0.05

    # Sliding window (s): each window is window_s long, and windows start hop_s apart.
    window_s: float = 60.0
    hop_s: float = 15.0

    # A window is only measured if it has enough GPS samples and no long silence
    # in GPS or VCU...
    min_samples: int = 30
    max_gap_s: float = 5.0
    # ...and is real driving: moving often enough, with speed that changes.
    moving_mph: float = 5.0
    min_moving_frac: float = 0.3
    min_speed_range_mph: float = 6.0

    # The best lag must beat every lag rival_min_s..rival_max_s away from it by
    # margin_mph, or the window can't tell them apart and gives no answer.
    rival_min_s: float = 1.0
    rival_max_s: float = 3.0
    margin_mph: float = 0.3

    # Per-sample error cap, so one bad sample can't dominate a window.
    trunc_mph: float = 5.0

    # Scale estimation (GPS reads a few % low vs VCU; one run ~30% low).
    min_moving_scale_mph: float = 2.0
    scale_iterations: int = 1

    # Run sanity: a fitted scale outside [min_scale, max_scale], or fewer measured
    # windows than min_windows, means nothing trustworthy was measured -> all default.
    min_scale: float = 0.6
    max_scale: float = 1.1
    min_windows: int = 3

    # Lag used when nothing in the run can be measured. The clean step overrides
    # this with GPS_TIME_OFFSET_S from settings.
    default_lag_s: float = 3.0
