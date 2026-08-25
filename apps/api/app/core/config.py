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

    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024

    weather_request_timeout_seconds: float = 5.0
    weather_cache_ttl_seconds: int = 1800

    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_base_url: str = "https://test.api.amadeus.com"
    flights_request_timeout_seconds: float = 5.0
    flights_cache_ttl_seconds: int = 300
    hotels_request_timeout_seconds: float = 5.0
    hotels_cache_ttl_seconds: int = 120
    openrouteservice_api_key: str = ""
    openrouteservice_base_url: str = "https://api.openrouteservice.org"
    distance_request_timeout_seconds: float = 5.0
    distance_cache_ttl_seconds: int = 600
    google_places_api_key: str = ""
    google_places_base_url: str = "https://places.googleapis.com"
    places_request_timeout_seconds: float = 5.0
    places_cache_ttl_seconds: int = 600
    frankfurter_base_url: str = "https://api.frankfurter.dev"
    currency_request_timeout_seconds: float = 5.0
    currency_cache_ttl_seconds: int = 86_400
    agent_tool_concurrency_limit: int = 4

    rag_embedding_provider: str = "fake"
    rag_embedding_model: str = "text-embedding-3-small"
    rag_embedding_dimensions: int = 1536
    rag_embedding_timeout_seconds: float = 30.0
    rag_chunk_target_tokens: int = 400
    rag_freshness_warning_days: int = 365
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

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
