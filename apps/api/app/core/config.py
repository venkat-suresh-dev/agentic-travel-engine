"""Application configuration."""

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Trip Planner API"
    api_prefix: str = ""

    postgres_user: str = "trip_planner"
    postgres_password: str = "trip_planner"
    postgres_db: str = "trip_planner"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
