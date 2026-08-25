"""Itinerary builder orchestration."""

from __future__ import annotations

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import build_grounded_catalog
from app.itinerary.composer.base import ItineraryComposer
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.materializer import materialize_itinerary
from app.itinerary.schemas import (
    ItineraryBuildResult,
    ItineraryValidationIssue,
    ItineraryValidationResult,
)
from app.itinerary.validator import validate_candidate, validate_itinerary


class ItineraryBuilder:
    """Compose, materialize, and validate grounded itineraries."""

    def __init__(
        self,
        *,
        composer: ItineraryComposer | None = None,
        assumptions: SchedulingAssumptions | None = None,
    ) -> None:
        self._composer = composer or FakeItineraryComposer()
        self._assumptions = assumptions or SchedulingAssumptions()

    def build_from_context(
        self, context: ItineraryBuildContext
    ) -> ItineraryBuildResult:
        catalog = build_grounded_catalog(
            context,
            indoor_types=self._assumptions.indoor_attraction_types,
        )
        try:
            candidate = self._composer.compose(context=context, catalog=catalog)
        except ValueError as exc:
            return ItineraryBuildResult(
                success=False,
                validation=ItineraryValidationResult(
                    is_valid=False,
                    issues=[
                        ItineraryValidationIssue(
                            code="composition_failed",
                            message=str(exc),
                        )
                    ],
                ),
            )
        candidate_validation = validate_candidate(
            candidate, context=context, catalog=catalog
        )
        if not candidate_validation.is_valid:
            return ItineraryBuildResult(
                success=False,
                candidate=candidate,
                validation=candidate_validation,
                composer_provider=type(self._composer).__name__,
            )

        itinerary = materialize_itinerary(
            candidate,
            context=context,
            catalog=catalog,
            assumptions=self._assumptions,
        )
        itinerary_validation = validate_itinerary(
            itinerary,
            context=context,
            catalog=catalog,
        )
        if not itinerary_validation.is_valid:
            return ItineraryBuildResult(
                success=False,
                candidate=candidate,
                validation=itinerary_validation,
                composer_provider=type(self._composer).__name__,
            )

        return ItineraryBuildResult(
            success=True,
            itinerary=itinerary,
            candidate=candidate,
            validation=ItineraryValidationResult(is_valid=True),
            composer_provider=type(self._composer).__name__,
        )
