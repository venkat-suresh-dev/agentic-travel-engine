"""Application configuration."""

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Trip Planner API"
    api_prefix: str = "/api"

    postgres_user: str = "trip_planner"
    postgres_password: str = "trip_planner"
    postgres_db: str = "trip_planner"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    clerk_secret_key: str = ""
    clerk_jwt_key: str | None = None
    clerk_authorized_parties: list[str] = Field(
        default_factory=lambda: ["http://localhost:3002"]
    )

    @field_validator("clerk_authorized_parties", mode="before")
    @classmethod
    def parse_authorized_parties(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [party.strip() for party in value.split(",") if party.strip()]
        if isinstance(value, list):
            return value
        raise TypeError("clerk_authorized_parties must be a string or list")

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
