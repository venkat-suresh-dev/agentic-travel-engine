"""Fuse Wikipedia reference landmarks with Geoapify POI candidates."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Protocol

from mcp_tools.places.reference.schemas import (
    LandmarkSearchRequest,
    LandmarkSearchResult,
    ReferenceLandmark,
    SignificanceTier,
)
from mcp_tools.places.reference.wikipedia import WikipediaLandmarkProvider

from app.budget.schemas import PriceDataKind
from app.itinerary.catalog import (
    GroundedAttraction,
    GroundedCatalog,
    _is_indoor_type,
    _normalize_primary_type,
)
from app.itinerary.context import ItineraryBuildContext

MATCH_RADIUS_KM = 0.85
NAME_MATCH_THRESHOLD = 0.45
MAX_REFERENCE_DISTANCE_KM = 22.0

_LANDMARK_TIERS = frozenset(
    {SignificanceTier.LANDMARK, SignificanceTier.REFERENCE_LANDMARK}
)


class LandmarkProvider(Protocol):
    def search_landmarks(
        self,
        request: LandmarkSearchRequest,
    ) -> LandmarkSearchResult: ...


@dataclass
class FusionStats:
    geoapify_candidates: int = 0
    reference_candidates: int = 0
    matched_to_geoapify: int = 0
    reference_only_added: int = 0
    fused_candidates: int = 0
    landmark_tier_candidates: int = 0


def fuse_reference_landmarks(
    catalog: GroundedCatalog,
    context: ItineraryBuildContext,
    *,
    provider: LandmarkProvider | None = None,
) -> FusionStats:
    """Merge reference landmarks into the grounded attraction catalog."""
    stats = FusionStats(geoapify_candidates=len(catalog.attractions))
    center = _destination_center(context, catalog)
    if center is None:
        stats.fused_candidates = len(catalog.attractions)
        stats.landmark_tier_candidates = _count_landmark_tier(catalog)
        return stats

    destination_name = context.trip_request.destination or "destination"
    duration = context.trip_request.duration_days or 5
    radius_meters = min(25_000, max(10_000, 8_000 + duration * 2_000))
    latitude, longitude = center

    wiki = provider or WikipediaLandmarkProvider()
    landmarks = _collect_reference_landmarks(
        wiki,
        destination_name=destination_name,
        centers=_search_centers(context, catalog, latitude, longitude),
        primary_center=(latitude, longitude),
        radius_meters=radius_meters,
        max_results=min(30, max(15, duration * 5)),
    )
    if not landmarks:
        stats.fused_candidates = len(catalog.attractions)
        stats.landmark_tier_candidates = _count_landmark_tier(catalog)
        return stats

    stats.reference_candidates = len(landmarks)
    matched_place_ids: set[str] = set()

    for landmark in landmarks:
        match_id = _find_geoapify_match(landmark, catalog)
        if match_id is not None:
            catalog.attractions[match_id] = _enrich_with_reference(
                catalog.attractions[match_id],
                landmark,
            )
            matched_place_ids.add(match_id)
            stats.matched_to_geoapify += 1
            continue

        if landmark.place_id in catalog.attractions:
            continue

        catalog.attractions[landmark.place_id] = _reference_attraction(landmark)
        stats.reference_only_added += 1

    stats.fused_candidates = len(catalog.attractions)
    stats.landmark_tier_candidates = _count_landmark_tier(catalog)
    return stats


def is_landmark_tier(attraction: GroundedAttraction) -> bool:
    return attraction.significance_tier in _LANDMARK_TIERS


def score_reference_landmark(landmark: ReferenceLandmark) -> float:
    """Deterministic significance score from reference evidence."""
    score = 0.55
    if landmark.distance_meters is not None:
        if landmark.distance_meters <= 3_000:
            score += 0.15
        elif landmark.distance_meters <= 8_000:
            score += 0.08
    if landmark.significance_tier == SignificanceTier.LANDMARK:
        score += 0.2
    if len(landmark.name.strip()) >= 6:
        score += 0.05
    return max(0.0, min(1.0, score))


def _enrich_with_reference(
    attraction: GroundedAttraction,
    landmark: ReferenceLandmark,
) -> GroundedAttraction:
    tier = _max_tier(attraction.significance_tier, landmark.significance_tier)
    quality = max(
        attraction.quality_score or 0.0,
        score_reference_landmark(landmark),
    )
    return replace(
        attraction,
        significance_tier=tier,
        quality_score=quality,
        reference_page_id=landmark.reference_page_id,
        reference_source=landmark.source,
    )


def _reference_attraction(landmark: ReferenceLandmark) -> GroundedAttraction:
    primary_type = _normalize_primary_type(None, landmark.name)
    quality = score_reference_landmark(landmark)
    return GroundedAttraction(
        place_id=landmark.place_id,
        name=landmark.name,
        latitude=landmark.latitude,
        longitude=landmark.longitude,
        primary_type=primary_type,
        source=landmark.source,
        data_status=PriceDataKind.REFERENCE,
        is_indoor=_is_indoor_type(
            primary_type, GroundedCatalog().indoor_attraction_types
        ),
        significance_tier=landmark.significance_tier,
        quality_score=quality,
        reference_page_id=landmark.reference_page_id,
        reference_source=landmark.source,
    )


def _find_geoapify_match(
    landmark: ReferenceLandmark,
    catalog: GroundedCatalog,
) -> str | None:
    best_id: str | None = None
    best_score = 0.0
    for place_id, attraction in catalog.attractions.items():
        if attraction.data_status == PriceDataKind.REFERENCE:
            continue
        distance = _haversine_km(
            landmark.latitude,
            landmark.longitude,
            attraction.latitude,
            attraction.longitude,
        )
        if distance > MATCH_RADIUS_KM:
            continue
        similarity = _name_similarity(landmark.name, attraction.name)
        if similarity < NAME_MATCH_THRESHOLD:
            continue
        combined = similarity + max(0.0, 1.0 - distance / MATCH_RADIUS_KM) * 0.25
        if combined > best_score:
            best_score = combined
            best_id = place_id
    return best_id


def _max_tier(
    current: SignificanceTier, incoming: SignificanceTier
) -> SignificanceTier:
    order = {
        SignificanceTier.POI: 0,
        SignificanceTier.REFERENCE_LANDMARK: 1,
        SignificanceTier.LANDMARK: 2,
    }
    return incoming if order[incoming] > order[current] else current


def _collect_reference_landmarks(
    wiki: LandmarkProvider,
    *,
    destination_name: str,
    centers: list[tuple[float, float]],
    primary_center: tuple[float, float],
    radius_meters: int,
    max_results: int,
) -> list[ReferenceLandmark]:
    merged: dict[str, ReferenceLandmark] = {}
    per_center = max(10, max_results // max(1, len(centers)))
    primary_lat, primary_lng = primary_center
    for lat, lng in centers:
        if (
            _haversine_km(primary_lat, primary_lng, lat, lng)
            > MAX_REFERENCE_DISTANCE_KM
        ):
            continue
        result = wiki.search_landmarks(
            LandmarkSearchRequest(
                destination_name=destination_name,
                latitude=lat,
                longitude=lng,
                radius_meters=radius_meters,
                max_results=per_center,
            )
        )
        for landmark in result.landmarks:
            if (
                _haversine_km(
                    primary_lat,
                    primary_lng,
                    landmark.latitude,
                    landmark.longitude,
                )
                > MAX_REFERENCE_DISTANCE_KM
            ):
                continue
            merged.setdefault(landmark.place_id, landmark)
    ranked = sorted(
        merged.values(),
        key=lambda item: (
            0 if item.significance_tier == SignificanceTier.LANDMARK else 1,
            item.distance_meters if item.distance_meters is not None else 99_999,
        ),
    )
    return ranked[:max_results]


def _search_centers(
    context: ItineraryBuildContext,
    catalog: GroundedCatalog,
    default_lat: float,
    default_lng: float,
) -> list[tuple[float, float]]:
    centers: list[tuple[float, float]] = [(default_lat, default_lng)]

    live_attractions = [
        item
        for item in catalog.attractions.values()
        if item.data_status != PriceDataKind.REFERENCE
    ]
    if live_attractions:
        lats = sorted(item.latitude for item in live_attractions)
        lngs = sorted(item.longitude for item in live_attractions)
        median = (lats[len(lats) // 2], lngs[len(lngs) // 2])
        if _haversine_km(default_lat, default_lng, median[0], median[1]) <= 12.0:
            centers.append(median)
        if len(lats) >= 4:
            spread_lat = lats[int(len(lats) * 0.75)]
            spread_lng = lngs[int(len(lngs) * 0.75)]
            if _haversine_km(default_lat, default_lng, spread_lat, spread_lng) <= 15.0:
                centers.append((spread_lat, spread_lng))

    hotel_search = context.hotel_search
    if hotel_search is not None:
        for hotel in hotel_search.hotels:
            if hotel.latitude is None or hotel.longitude is None:
                continue
            if (
                _haversine_km(default_lat, default_lng, hotel.latitude, hotel.longitude)
                <= 8.0
            ):
                centers.append((hotel.latitude, hotel.longitude))
                break

    deduped: list[tuple[float, float]] = []
    for center in centers:
        if not any(
            _haversine_km(center[0], center[1], lat, lng) < 2.0 for lat, lng in deduped
        ):
            deduped.append(center)
    return deduped[:3]


def _destination_center(
    context: ItineraryBuildContext,
    catalog: GroundedCatalog,
) -> tuple[float, float] | None:
    search = context.attraction_search
    if search is not None and search.attractions:
        lats = sorted(item.latitude for item in search.attractions)
        lngs = sorted(item.longitude for item in search.attractions)
        return lats[len(lats) // 2], lngs[len(lngs) // 2]

    live_attractions = [
        item
        for item in catalog.attractions.values()
        if item.data_status != PriceDataKind.REFERENCE
    ]
    if live_attractions:
        lats = sorted(item.latitude for item in live_attractions)
        lngs = sorted(item.longitude for item in live_attractions)
        return lats[len(lats) // 2], lngs[len(lngs) // 2]

    return None


def _count_landmark_tier(catalog: GroundedCatalog) -> int:
    return sum(1 for item in catalog.attractions.values() if is_landmark_tier(item))


def _normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    return " ".join(cleaned.split())


def _name_similarity(left: str, right: str) -> float:
    left_norm = _normalize_name(left)
    right_norm = _normalize_name(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.85
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(len(left_tokens), len(right_tokens))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
