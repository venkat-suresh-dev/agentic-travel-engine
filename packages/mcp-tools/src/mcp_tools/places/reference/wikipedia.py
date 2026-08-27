"""Wikipedia geographic search for landmark/reference discovery."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx

from mcp_tools.places.reference.schemas import (
    LandmarkSearchRequest,
    LandmarkSearchResult,
    ReferenceLandmark,
    ReferenceLandmarkStatus,
    SignificanceTier,
)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SOURCE = "wikipedia"
DEFAULT_TIMEOUT_SECONDS = 8.0
DEFAULT_USER_AGENT = (
    "AgenticTravelEngine/1.0 (https://github.com/agentic-travel-engine; demo@local)"
)

_SKIP_TITLE_PATTERNS = (
    re.compile(r"\(disambiguation\)", re.I),
    re.compile(r"^list of ", re.I),
    re.compile(r"^timeline of ", re.I),
    re.compile(r"^history of ", re.I),
    re.compile(r"^economy of ", re.I),
    re.compile(r"^transport in ", re.I),
)

_LOW_SIGNAL_PATTERNS = (
    re.compile(r"\b(company|corporation|school|university|hospital)\b", re.I),
    re.compile(r"\b(district|suburb|neighbourhood|neighborhood)\b", re.I),
)

_HOTEL_PATTERN = re.compile(
    r"\b(hotel|rotana|kempinski|sheraton|gevora|marriott|hyatt|hilton|thani)\b",
    re.I,
)
_METRO_PATTERN = re.compile(r"\(.*metro.*\)", re.I)
_RESTAURANT_PATTERN = re.compile(
    r"\b(ristorante|restaurant|at\.mosphere)\b",
    re.I,
)
_GENERIC_TOWER_PATTERN = re.compile(r"^[A-Za-z0-9 .'-]+\s+Tower$", re.I)


class WikipediaLandmarkProvider:
    """Discover landmarks via Wikipedia geosearch (no API key required)."""

    def __init__(
        self,
        *,
        base_url: str = WIKIPEDIA_API,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._client = client

    def search_landmarks(
        self,
        request: LandmarkSearchRequest,
    ) -> LandmarkSearchResult:
        retrieved_at = datetime.now(UTC)
        try:
            landmarks = self._fetch_geosearch(request)
            return LandmarkSearchResult(
                source=WIKIPEDIA_SOURCE,
                retrieved_at=retrieved_at,
                data_status=ReferenceLandmarkStatus.LIVE,
                landmarks=landmarks,
            )
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            return LandmarkSearchResult.unavailable(
                source=WIKIPEDIA_SOURCE,
                retrieved_at=retrieved_at,
                error_message=str(exc),
            )

    def _fetch_geosearch(
        self,
        request: LandmarkSearchRequest,
    ) -> list[ReferenceLandmark]:
        params: dict[str, str | int | float] = {
            "action": "query",
            "list": "geosearch",
            "gscoord": f"{request.latitude}|{request.longitude}",
            "gsradius": min(request.radius_meters, 10_000),
            "gslimit": min(50, max(request.max_results * 2, request.max_results)),
            "format": "json",
        }
        payload = self._get(params)
        pages = payload.get("query", {}).get("geosearch", [])
        if not isinstance(pages, list):
            return []

        landmarks: list[ReferenceLandmark] = []
        for page in pages:
            parsed = self._parse_page(page, destination_name=request.destination_name)
            if parsed is not None:
                landmarks.append(parsed)
        landmarks.sort(
            key=lambda item: (
                0 if item.significance_tier == SignificanceTier.LANDMARK else 1,
                item.distance_meters if item.distance_meters is not None else 99_999,
            )
        )
        return landmarks[: request.max_results]

    def _parse_page(
        self,
        page: dict[str, Any],
        *,
        destination_name: str,
    ) -> ReferenceLandmark | None:
        title = page.get("title")
        page_id = page.get("pageid")
        lat = page.get("lat")
        lon = page.get("lon")
        if not isinstance(title, str) or not isinstance(page_id, int):
            return None
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None
        if any(pattern.search(title) for pattern in _SKIP_TITLE_PATTERNS):
            return None
        if any(pattern.search(title) for pattern in _LOW_SIGNAL_PATTERNS):
            return None
        if _should_skip_title(title, destination_name):
            return None

        dist = page.get("dist")
        distance_meters = int(dist) if isinstance(dist, (int, float)) else None
        tier = _infer_significance_tier(title)
        if tier != SignificanceTier.LANDMARK and not _has_tourism_signal(title):
            return None

        return ReferenceLandmark(
            place_id=f"wikipedia:{page_id}",
            name=title,
            latitude=float(lat),
            longitude=float(lon),
            source=WIKIPEDIA_SOURCE,
            reference_page_id=page_id,
            significance_tier=tier,
            distance_meters=distance_meters,
        )

    def _get(self, params: dict[str, str | int | float]) -> dict[str, Any]:
        url = self._base_url
        headers = {"User-Agent": self._user_agent}
        if self._client is not None:
            response = self._client.get(
                url,
                params=params,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        else:
            with httpx.Client(timeout=self._timeout_seconds, headers=headers) as client:
                response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            msg = "Wikipedia response was not an object"
            raise ValueError(msg)
        return payload


def _infer_significance_tier(title: str) -> SignificanceTier:
    lowered = title.lower()
    landmark_tokens = (
        "tower",
        "museum",
        "mosque",
        "palace",
        "fort",
        "frame",
        "fountain",
        "aquarium",
        "opera",
        "cathedral",
        "temple",
        "marina",
        "creek",
        "island",
        "garden",
        "park",
        "souk",
        "souq",
        "bazaar",
        "archipelago",
        "world",
        "burj",
        "mall",
        "arena",
        "planet",
        "walk",
        "zoo",
        "heritage",
        "gallery",
    )
    if any(token in lowered for token in landmark_tokens):
        return SignificanceTier.LANDMARK
    return SignificanceTier.REFERENCE_LANDMARK


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def _should_skip_title(title: str, destination_name: str) -> bool:
    if _normalize_title(title) == _normalize_title(destination_name):
        return True
    if _HOTEL_PATTERN.search(title):
        return True
    if _METRO_PATTERN.search(title):
        return True
    if _RESTAURANT_PATTERN.search(title):
        return True
    if _GENERIC_TOWER_PATTERN.match(title) and "burj" not in title.lower():
        return True
    if re.search(r"\b(plaza|boulevard)\b", title, re.I) and not _has_tourism_signal(
        title
    ):
        return True
    return False


def _has_tourism_signal(title: str) -> bool:
    return _infer_significance_tier(title) == SignificanceTier.LANDMARK
