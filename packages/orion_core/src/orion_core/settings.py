"""Single source of configuration for every Orion service (read from env / .env)."""

from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # OrionDB: ours, read/write. Engines add the driver (+asyncpg / +psycopg).
    orion_database_url: str
    # Penelope or penelope2: read-only. Swapping between them is just this URL.
    penelope_database_url: str | None = None
    # Where the backend reaches the pipeline API.
    pipeline_api_url: str = "http://localhost:8200"
    # How many rows each extract section can pull at once.
    pipeline_page_size: int = 100_000
    # Seconds added to lagged sensors' timestamps (gps_lagged in sensor_catalog), by both
    # the clean step and the backend sensors API. 0 disables the correction.
    gps_time_offset_s: float = 3.0
    # The backend sensors API gives each reading the lap_percent of the nearest
    # estimated position within this many seconds, or null if there's none.
    lap_percent_match_tolerance_s: float = 0.05

    # Lap detection (see docs/lap_detection.md). Untuned starting guesses.
    # Radius of each remembered point's hitbox, in meters.
    lap_hitbox_radius_m: float = 3.0
    # Minimum time between two points for a revisit to count, in seconds.
    lap_min_revisit_time_s: float = 5.0
    # Minimum distance driven between two points for a revisit to count, in meters.
    lap_min_revisit_distance_m: float = 50.0
    # Searching for the gate only looks at every Nth point. 1 uses every point.
    lap_gate_search_sample_every: int = 5
    # The gate reaches this far on each side of its center, in meters.
    lap_gate_half_width_m: float = 15.0
    # Minimum time between two counted gate crossings, in seconds.
    lap_min_lap_time_s: float = 10.0

    # Lap progress (see docs/lap_progress.md). Untuned starting guesses.
    # A lap slower than this times the median lap is an outlier (a long stop, a hole
    # in the data, or laps merged by a missed crossing), so it can't be the ideal lap.
    lap_progress_max_lap_time_ratio: float = 1.5
    # Distance between the points of each resampled lap, in meters.
    lap_progress_spacing_m: float = 1.0
    # How far, as an RMS, smoothing may move the ideal lap off the medoid lap's
    # points to iron out jitter, in meters.
    lap_progress_smoothing_m: float = 0.25
    # Points farther than this from the ideal lap are off track, in meters.
    lap_progress_max_offtrack_m: float = 15.0
    # Points heading more than this far from the ideal lap's direction are off track
    # (spins, wrong way), in degrees.
    lap_progress_max_heading_diff_deg: float = 60.0
    # Points slower than this get no percentage, in meters per second.
    lap_progress_min_speed_mps: float = 1.0
    # When matching, each unit of heading counts as this many meters, so a full
    # turn-around adds 2 x this to the distance and the far side of a hairpin
    # (driven the other way) never looks closest.
    lap_progress_heading_weight_m: float = 10.0
    # A lap's first points within this many meters before the start/finish line read
    # 0%, and its last points within this many meters past it read 100%.
    lap_progress_gate_margin_m: float = 20.0
    # A match further ahead of the car's furthest progress than it could drive at
    # this speed, plus `lap_progress_jump_margin_m`, is a bad match and gets no
    # percentage, in meters per second.
    lap_progress_max_speed_mps: float = 40.0
    # Slack for matching noise in that check, in meters.
    lap_progress_jump_margin_m: float = 10.0


class SettingsError(RuntimeError):
    pass


def _describe(error: ValidationError) -> str:
    # Describes the .env file issues
    lines = ["Invalid Orion settings:"]
    for err in error.errors():
        env_var = str(err["loc"][0]).upper()
        problem = "not set" if err["type"] == "missing" else err["msg"]
        lines.append(f"  {env_var}: {problem}")

    env_path = Path(ENV_FILE).resolve()
    found = "found" if env_path.exists() else "NOT FOUND"
    lines.append(f"Read from the environment and {env_path} ({found}).")
    lines.append("See .env.example at the repo root for the expected variables.")
    return "\n".join(lines)


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        raise SettingsError(_describe(e)) from None
