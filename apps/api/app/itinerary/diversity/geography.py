"""Geographic clustering for multi-day itinerary variety."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.itinerary.catalog import GroundedAttraction, GroundedCatalog


@dataclass(frozen=True, slots=True)
class GeographicRegion:
    """A derived geographic zone from candidate coordinates."""

    region_id: int
    label: str
    centroid_lat: float
    centroid_lng: float
    attraction_ids: tuple[str, ...]


def cluster_attractions(
    catalog: GroundedCatalog,
    *,
    num_regions: int,
    center_lat: float | None = None,
    center_lng: float | None = None,
) -> list[GeographicRegion]:
    """Cluster attractions into geographic regions using coordinate angles.

    Regions are derived from provider coordinates — not hard-coded city names.
    When ``center_lat``/``center_lng`` are supplied they anchor clustering to the
    destination spread instead of the POI-density centroid.
    """
    attractions = list(catalog.attractions.values())
    if not attractions:
        return []

    region_count = max(1, min(num_regions, len(attractions)))
    if region_count == 1:
        return [_single_region(attractions)]

    if center_lat is not None and center_lng is not None:
        anchor_lat, anchor_lng = center_lat, center_lng
    else:
        anchor_lat = sum(item.latitude for item in attractions) / len(attractions)
        anchor_lng = sum(item.longitude for item in attractions) / len(attractions)

    buckets: dict[int, list[GroundedAttraction]] = {
        index: [] for index in range(region_count)
    }
    for attraction in attractions:
        angle = math.atan2(
            attraction.latitude - anchor_lat,
            attraction.longitude - anchor_lng,
        )
        bucket = int((angle + math.pi) / (2 * math.pi) * region_count) % region_count
        buckets[bucket].append(attraction)

    regions: list[GeographicRegion] = []
    for region_id, members in sorted(buckets.items()):
        if not members:
            continue
        regions.append(_region_from_members(region_id, members))
    return regions


def region_for_attraction(
    attraction_id: str,
    regions: list[GeographicRegion],
) -> int | None:
    for region in regions:
        if attraction_id in region.attraction_ids:
            return region.region_id
    return None


def _single_region(attractions: list[GroundedAttraction]) -> GeographicRegion:
    return _region_from_members(0, attractions)


def _region_from_members(
    region_id: int,
    members: list[GroundedAttraction],
) -> GeographicRegion:
    centroid_lat = sum(item.latitude for item in members) / len(members)
    centroid_lng = sum(item.longitude for item in members) / len(members)
    label = _derive_region_label(members, centroid_lat, centroid_lng)
    return GeographicRegion(
        region_id=region_id,
        label=label,
        centroid_lat=centroid_lat,
        centroid_lng=centroid_lng,
        attraction_ids=tuple(item.place_id for item in members),
    )


def _derive_region_label(
    members: list[GroundedAttraction],
    centroid_lat: float,
    centroid_lng: float,
) -> str:
    """Derive a short region label from dominant category and relative position."""
    type_counts: dict[str, int] = {}
    for member in members:
        primary = member.primary_type or "area"
        type_counts[primary] = type_counts.get(primary, 0) + 1
    dominant = max(type_counts, key=lambda key: type_counts[key])

    type_labels = {
        "museum": "Cultural quarter",
        "art_gallery": "Arts district",
        "park": "Green spaces",
        "historical_landmark": "Heritage area",
        "place_of_worship": "Historic quarter",
        "shopping_mall": "Retail district",
        "tourist_attraction": "City highlights",
        "zoo": "Leisure zone",
        "amusement_park": "Entertainment zone",
    }
    return type_labels.get(dominant, "Local area")
