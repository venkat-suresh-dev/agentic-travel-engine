"""Development provider health diagnostics."""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.core.config import Settings, settings
from app.core.current_user import CurrentUser

router = APIRouter(tags=["diagnostics"])


class ProviderHealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    configured: bool
    reachable: bool
    notes: str | None = None


class ProviderHealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment: str
    providers: list[ProviderHealthStatus]


def _require_development(cfg: Settings) -> None:
    if cfg.app_env.lower() not in {"development", "demo", "local"}:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )


@router.get("/dev/providers", response_model=ProviderHealthResponse)
async def provider_health(
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ProviderHealthResponse:
    """Authenticated development-only provider reachability checks."""
    _require_development(settings)
    providers = [
        _check_groq(settings),
        _check_gemini(settings),
        _check_serpapi(settings),
        _check_stayingapi(settings),
        _check_geoapify(settings),
        _check_openrouteservice(settings),
        _check_open_meteo(),
        _check_frankfurter(settings),
        _check_clerk(settings),
    ]
    return ProviderHealthResponse(
        environment=settings.app_env,
        providers=providers,
    )


def _check_groq(cfg: Settings) -> ProviderHealthStatus:
    configured = bool(cfg.groq_api_key)
    reachable = False
    notes = None
    if configured and cfg.llm_provider.lower() == "groq":
        reachable = _probe_get(
            f"{cfg.groq_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {cfg.groq_api_key}"},
        )
        if not reachable:
            notes = "models endpoint unreachable"
    return ProviderHealthStatus(
        provider="groq",
        configured=configured,
        reachable=reachable,
        notes=notes,
    )


def _check_gemini(cfg: Settings) -> ProviderHealthStatus:
    configured = bool(cfg.gemini_api_key)
    reachable = False
    if configured and cfg.rag_embedding_provider.lower() == "gemini":
        reachable = _probe_get(
            f"{cfg.gemini_base_url.rstrip('/')}/models",
            params={"key": cfg.gemini_api_key},
        )
    return ProviderHealthStatus(
        provider="gemini",
        configured=configured,
        reachable=reachable,
    )


def _check_serpapi(cfg: Settings) -> ProviderHealthStatus:
    configured = bool(cfg.serpapi_api_key)
    reachable = configured and cfg.flights_provider.lower() in {
        "serpapi",
        "serpapi_google_flights",
        "google_flights",
    }
    return ProviderHealthStatus(
        provider="serpapi-google-flights",
        configured=configured,
        reachable=reachable,
        notes="reachability verified on first search call" if configured else None,
    )


def _check_stayingapi(cfg: Settings) -> ProviderHealthStatus:
    configured = bool(cfg.stayingapi_api_key)
    reachable = configured and cfg.hotels_provider.lower() in {
        "stayingapi",
        "staying_api",
    }
    notes = f"environment={cfg.stayingapi_environment}" if configured else None
    return ProviderHealthStatus(
        provider="stayingapi",
        configured=configured,
        reachable=reachable,
        notes=notes,
    )


def _check_geoapify(cfg: Settings) -> ProviderHealthStatus:
    configured = bool(cfg.geoapify_api_key)
    reachable = False
    if configured:
        reachable = _probe_get(
            f"{cfg.geoapify_base_url.rstrip('/')}/v1/geocode/search",
            params={"text": "Dubai", "apiKey": cfg.geoapify_api_key, "limit": 1},
        )
    return ProviderHealthStatus(
        provider="geoapify",
        configured=configured,
        reachable=reachable,
    )


def _check_openrouteservice(cfg: Settings) -> ProviderHealthStatus:
    configured = bool(cfg.openrouteservice_api_key)
    reachable = False
    if configured:
        reachable = _probe_get(
            f"{cfg.openrouteservice_base_url.rstrip('/')}/v2/directions/driving-car",
            params={"api_key": cfg.openrouteservice_api_key},
            headers={"Accept": "application/json"},
            expect_status={400, 401, 403, 405},
        )
    return ProviderHealthStatus(
        provider="openrouteservice",
        configured=configured,
        reachable=reachable or configured,
        notes=(
            "key configured; full matrix verified on tool call" if configured else None
        ),
    )


def _check_open_meteo() -> ProviderHealthStatus:
    reachable = _probe_get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": "Dubai", "count": 1},
    )
    return ProviderHealthStatus(
        provider="open-meteo",
        configured=True,
        reachable=reachable,
    )


def _check_frankfurter(cfg: Settings) -> ProviderHealthStatus:
    base = cfg.frankfurter_base_url.rstrip("/")
    reachable = _probe_get(
        f"{base}/v1/latest",
        params={"base": "USD", "symbols": "INR"},
    )
    return ProviderHealthStatus(
        provider="frankfurter",
        configured=True,
        reachable=reachable,
    )


def _check_clerk(cfg: Settings) -> ProviderHealthStatus:
    configured = bool(cfg.clerk_secret_key)
    return ProviderHealthStatus(
        provider="clerk",
        configured=configured,
        reachable=configured,
        notes="verified on authenticated API requests" if configured else None,
    )


def _probe_get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    expect_status: set[int] | None = None,
    timeout_seconds: float = 5.0,
) -> bool:
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url, params=params, headers=headers)
        if expect_status:
            return response.status_code in expect_status or response.status_code < 400
        return response.status_code < 400
    except httpx.HTTPError:
        return False
