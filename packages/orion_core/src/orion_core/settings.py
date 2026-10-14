"""Single source of configuration for every Orion service (read from env / .env)."""

from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OrionDB: ours, read/write. Engines add the driver (+asyncpg / +psycopg).
    orion_database_url: str
    # Penelope or penelope2: read-only. Swapping between them is just this URL.
    penelope_database_url: str | None = None
    # Where the backend reaches the pipeline API.
    pipeline_api_url: str = "http://localhost:8200"
    # How many rows each extract section can pull at once.
    pipeline_page_size: int = 100_000


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
