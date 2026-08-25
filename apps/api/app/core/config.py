"""Application configuration."""

from pydantic import AliasChoices, Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Trip Planner API"
    app_env: str = "development"
    app_mode: str = "demo"
    api_prefix: str = "/api"
    frontend_origin: str = "http://localhost:3002"

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
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_max_tokens: int = 1024

    weather_provider: str = "open_meteo"
    weather_request_timeout_seconds: float = 5.0
    weather_cache_ttl_seconds: int = 1800

    flights_provider: str = Field(
        default="amadeus",
        validation_alias=AliasChoices("flights_provider", "FLIGHTS_PROVIDER"),
    )
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_base_url: str = "https://test.api.amadeus.com"
    serpapi_api_key: str = ""
    serpapi_base_url: str = "https://serpapi.com/search"
    serpapi_flights_engine: str = "google_flights"
    flights_request_timeout_seconds: float = 5.0
    flights_cache_ttl_seconds: int = 300

    hotels_provider: str = Field(
        default="amadeus",
        validation_alias=AliasChoices("hotels_provider", "HOTELS_PROVIDER"),
    )
    stayingapi_api_key: str = ""
    stayingapi_base_url: str = "https://api.stayingapi.com"
    stayingapi_environment: str = "sandbox"
    hotels_request_timeout_seconds: float = 5.0
    hotels_cache_ttl_seconds: int = 120

    distance_provider: str = "openrouteservice"
    openrouteservice_api_key: str = ""
    openrouteservice_base_url: str = "https://api.openrouteservice.org"
    distance_request_timeout_seconds: float = 5.0
    distance_cache_ttl_seconds: int = 600

    places_provider: str = Field(
        default="google",
        validation_alias=AliasChoices("places_provider", "PLACES_PROVIDER"),
    )
    google_places_api_key: str = ""
    google_places_base_url: str = "https://places.googleapis.com"
    geoapify_api_key: str = ""
    geoapify_base_url: str = "https://api.geoapify.com"
    geoapify_geocoding_enabled: bool = True
    places_request_timeout_seconds: float = 5.0
    places_cache_ttl_seconds: int = 600

    currency_provider: str = "frankfurter"
    frankfurter_base_url: str = "https://api.frankfurter.dev"
    currency_request_timeout_seconds: float = 5.0
    currency_cache_ttl_seconds: int = 86_400
    agent_tool_concurrency_limit: int = 4

    rag_embedding_provider: str = Field(
        default="fake",
        validation_alias=AliasChoices(
            "rag_embedding_provider",
            "embedding_provider",
            "EMBEDDING_PROVIDER",
        ),
    )
    rag_embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias=AliasChoices(
            "rag_embedding_model",
            "gemini_embedding_model",
            "GEMINI_EMBEDDING_MODEL",
        ),
    )
    rag_embedding_dimensions: int = Field(
        default=1536,
        validation_alias=AliasChoices(
            "rag_embedding_dimensions",
            "rag_embedding_dimension",
            "RAG_EMBEDDING_DIMENSION",
        ),
    )
    rag_embedding_timeout_seconds: float = 30.0
    rag_chunk_target_tokens: int = 400
    rag_freshness_warning_days: int = 365
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
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
