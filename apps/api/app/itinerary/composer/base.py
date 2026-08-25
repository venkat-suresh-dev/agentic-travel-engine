"""Itinerary composition interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.itinerary.catalog import GroundedCatalog
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.schemas import ItinerarySelectionCandidate


@runtime_checkable
class ItineraryComposer(Protocol):
    """LLM-backed itinerary composition boundary."""

    def compose(
        self,
        *,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
    ) -> ItinerarySelectionCandidate: ...
