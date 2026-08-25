"""Google Places API (New) field masks for cost-conscious requests."""

from __future__ import annotations

# Minimal field sets for the normalized restaurant and attraction schemas.
# Excludes reviews, photos, generative summaries, menus, and other expensive
# advanced fields not required by the current acceptance criteria.

RESTAURANT_SEARCH_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.primaryType",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.priceRange",
        "places.regularOpeningHours",
        "places.websiteUri",
    ]
)

ATTRACTION_SEARCH_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.primaryType",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.regularOpeningHours",
        "places.websiteUri",
    ]
)
