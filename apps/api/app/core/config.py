"""Application configuration."""

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "AI Trip Planner API"
    api_prefix: str = ""


settings = Settings()
