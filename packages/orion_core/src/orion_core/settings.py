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
    lap_gate_half_width_m: float = 5.0
    # Minimum time between two counted gate crossings, in seconds.
    lap_min_lap_time_s: float = 10.0


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
