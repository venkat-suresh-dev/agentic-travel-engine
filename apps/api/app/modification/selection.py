"""Deterministic grounded-catalog selection heuristics for modifications."""

from __future__ import annotations

from decimal import Decimal

from app.itinerary.catalog import GroundedCatalog, GroundedHotel

PRICE_LEVEL_RANK: dict[str, int] = {
    "inexpensive": 0,
    "moderate": 1,
    "expensive": 2,
    "very_expensive": 3,
}

CULTURE_TYPES = frozenset(
    {
        "museum",
        "art_gallery",
        "historical_landmark",
        "place_of_worship",
        "tourist_attraction",
    }
)
SHOPPING_TYPES = frozenset({"shopping_mall"})
CALM_TYPES = frozenset({"museum", "art_gallery", "park", "place_of_worship"})


def select_different_restaurant(
    catalog: GroundedCatalog,
    *,
    current_id: str | None,
    prefer_cheaper: bool,
    require_change: bool = True,
) -> str | None:
    restaurant_ids = catalog.restaurant_ids()
    if not restaurant_ids:
        return current_id
    alternatives = [item for item in restaurant_ids if item != current_id]
    if not alternatives:
        return current_id
    if prefer_cheaper:
        current_key = (
            _restaurant_cost_key(catalog, current_id)
            if current_id in catalog.restaurants
            else (99, 5.0)
        )
        cheaper = [
            item
            for item in alternatives
            if _restaurant_cost_key(catalog, item) < current_key
        ]
        if cheaper:
            return min(cheaper, key=lambda item: _restaurant_cost_key(catalog, item))
        if not require_change:
            return current_id
        return min(alternatives, key=lambda item: _restaurant_cost_key(catalog, item))
    return max(alternatives, key=lambda item: _restaurant_quality_key(catalog, item))


def select_different_attraction(
    catalog: GroundedCatalog,
    *,
    current_ids: list[str],
    exclude_ids: set[str] | None = None,
    prefer_cheaper: bool = False,
    prefer_calm: bool = False,
    prefer_culture: bool = False,
    avoid_shopping: bool = False,
    max_items: int = 1,
) -> list[str]:
    attraction_ids = catalog.attraction_ids()
    excluded = set(exclude_ids or ())
    excluded.update(current_ids)
    candidates = [item for item in attraction_ids if item not in excluded]
    if not candidates:
        candidates = [item for item in attraction_ids if item not in current_ids]
    if not candidates:
        return current_ids[:max_items]

    ranked = sorted(
        candidates,
        key=lambda item: _attraction_rank(
            catalog,
            item,
            prefer_cheaper=prefer_cheaper,
            prefer_calm=prefer_calm,
            prefer_culture=prefer_culture,
            avoid_shopping=avoid_shopping,
        ),
    )
    selected: list[str] = []
    for attraction_id in ranked:
        if len(selected) >= max_items:
            break
        selected.append(attraction_id)
    return selected or current_ids[:max_items]


def reduce_attractions(current_ids: list[str], *, max_items: int = 1) -> list[str]:
    if not current_ids:
        return []
    if len(current_ids) > max_items:
        return current_ids[:max_items]
    return list(current_ids)


def re_rank_for_preference(
    catalog: GroundedCatalog,
    current_ids: list[str],
    *,
    prefer_culture: bool,
    avoid_shopping: bool,
    max_items: int,
) -> list[str]:
    def allowed(attraction_id: str) -> bool:
        attraction = catalog.attractions.get(attraction_id)
        if attraction is None:
            return False
        primary = attraction.primary_type or ""
        if avoid_shopping and primary in SHOPPING_TYPES:
            return False
        if (
            prefer_culture
            and primary not in CULTURE_TYPES
            and primary in SHOPPING_TYPES
        ):
            return False
        return True

    kept = [item for item in current_ids if allowed(item)]
    dropped_shopping = any(
        (catalog.attractions[item].primary_type or "") in SHOPPING_TYPES
        for item in current_ids
        if item in catalog.attractions
    )
    pool = [item for item in catalog.attraction_ids() if allowed(item)]
    if prefer_culture:
        culture_pool = [
            item
            for item in pool
            if (catalog.attractions[item].primary_type or "") in CULTURE_TYPES
        ]
        if culture_pool:
            pool = culture_pool
            kept = [item for item in kept if item in culture_pool]

    replacements = [item for item in pool if item not in current_ids]
    selected: list[str] = []
    for item in kept + replacements:
        if item not in selected:
            selected.append(item)
    if dropped_shopping or replacements:
        return selected[: max(max_items, 1)] or current_ids[:max_items]
    return kept[:max_items] or current_ids[:max_items]


def select_hotel(
    catalog: GroundedCatalog,
    *,
    current_id: str | None,
    prefer_cheaper: bool = True,
    require_change: bool = True,
) -> str | None:
    hotels = list(catalog.hotels.values())
    if not hotels:
        return current_id
    alternatives = [hotel for hotel in hotels if hotel.hotel_id != current_id]
    if not alternatives:
        return current_id
    current_amount = _hotel_amount_for_id(catalog, current_id)
    if prefer_cheaper:
        cheaper = [
            hotel for hotel in alternatives if _hotel_amount(hotel) < current_amount
        ]
        if cheaper:
            return min(cheaper, key=_hotel_amount).hotel_id
        if not require_change:
            return current_id
    chosen = min(alternatives, key=_hotel_amount)
    return chosen.hotel_id


def _restaurant_cost_key(
    catalog: GroundedCatalog, restaurant_id: str
) -> tuple[int, float]:
    restaurant = catalog.restaurants[restaurant_id]
    rank = PRICE_LEVEL_RANK.get(restaurant.price_level or "", 1)
    rating = restaurant.rating if restaurant.rating is not None else 3.0
    return (rank, rating)


def _restaurant_quality_key(
    catalog: GroundedCatalog, restaurant_id: str
) -> tuple[float, int]:
    restaurant = catalog.restaurants[restaurant_id]
    rating = restaurant.rating if restaurant.rating is not None else 0.0
    count_proxy = 1 if restaurant.rating is not None else 0
    return (rating, count_proxy)


def _attraction_rank(
    catalog: GroundedCatalog,
    attraction_id: str,
    *,
    prefer_cheaper: bool,
    prefer_calm: bool,
    prefer_culture: bool,
    avoid_shopping: bool,
) -> tuple[int, int, float]:
    attraction = catalog.attractions[attraction_id]
    primary = attraction.primary_type or ""
    shopping_penalty = 2 if avoid_shopping and primary in SHOPPING_TYPES else 0
    culture_bonus = 0 if prefer_culture and primary in CULTURE_TYPES else 1
    calm_bonus = 0 if prefer_calm and primary in CALM_TYPES else 1
    cheaper_rank = PRICE_LEVEL_RANK.get(attraction.price_level or "", 1)
    rating = -(attraction.rating or 0.0)
    preference_score = shopping_penalty + culture_bonus + calm_bonus
    cost_score = cheaper_rank if prefer_cheaper else 0
    return (preference_score, cost_score, rating)


def _hotel_amount(hotel: GroundedHotel) -> Decimal:
    return hotel.total_amount if hotel.total_amount is not None else Decimal("0")


def _hotel_amount_for_id(catalog: GroundedCatalog, hotel_id: str | None) -> Decimal:
    if hotel_id is None:
        return Decimal("Infinity")
    hotel = catalog.hotels.get(hotel_id)
    if hotel is None:
        return Decimal("Infinity")
    return _hotel_amount(hotel)
