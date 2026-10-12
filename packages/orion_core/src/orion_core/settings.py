"""Single source of configuration for every Orion service (read from env / .env)."""

from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
