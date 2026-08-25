"""Itinerary generation package."""

from app.itinerary.composer import (
    FakeItineraryComposer,
    ItineraryComposer,
    LLMItineraryComposer,
)
from app.itinerary.schemas import (
    Itinerary,
    ItineraryBuildResult,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemCategory,
    ItinerarySelectionCandidate,
    ItineraryValidationResult,
    MealSuggestion,
    TravelLeg,
)

__all__ = [
    "FakeItineraryComposer",
    "Itinerary",
    "ItineraryBuildResult",
    "ItineraryBuilder",
    "ItineraryComposer",
    "ItineraryDay",
    "ItineraryItem",
    "ItineraryItemCategory",
    "ItinerarySelectionCandidate",
    "ItineraryValidationResult",
    "LLMItineraryComposer",
    "MealSuggestion",
    "TravelLeg",
    "build_itinerary_context_from_state",
]


def __getattr__(name: str) -> object:
    if name == "ItineraryBuilder":
        from app.itinerary.builder import ItineraryBuilder

        return ItineraryBuilder
    if name == "build_itinerary_context_from_state":
        from app.itinerary.from_state import build_itinerary_context_from_state

        return build_itinerary_context_from_state
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
