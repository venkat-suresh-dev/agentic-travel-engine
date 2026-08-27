"""Itinerary builder orchestration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog, build_grounded_catalog
from app.itinerary.composer.base import ItineraryComposer
from app.itinerary.composer.fake import FakeItineraryComposer
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.diversity.themes import DayTheme
from app.itinerary.materializer import materialize_itinerary
from app.itinerary.quality import filter_catalog_quality
from app.itinerary.schemas import (
    Itinerary,
    ItineraryBuildResult,
    ItinerarySelectionCandidate,
    ItineraryValidationIssue,
    ItineraryValidationResult,
)
from app.itinerary.validator import validate_candidate, validate_itinerary


class ItineraryDraftResult(BaseModel):
    """Compose and materialize an itinerary draft without critic approval."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    itinerary: Itinerary | None = None
    candidate: ItinerarySelectionCandidate | None = None
    composer_provider: str | None = None
    error_message: str | None = None


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

    def build_draft_from_context(
        self, context: ItineraryBuildContext
    ) -> ItineraryDraftResult:
        catalog = build_grounded_catalog(
            context,
            indoor_types=self._assumptions.indoor_attraction_types,
        )
        catalog, _quality_stats = filter_catalog_quality(catalog)
        try:
            candidate = self._composer.compose(context=context, catalog=catalog)
        except ValueError as exc:
            return ItineraryDraftResult(
                success=False,
                error_message=str(exc),
                composer_provider=type(self._composer).__name__,
            )

        candidate_validation = validate_candidate(
            candidate, context=context, catalog=catalog
        )
        if not candidate_validation.is_valid:
            return ItineraryDraftResult(
                success=True,
                candidate=candidate,
                composer_provider=type(self._composer).__name__,
            )

        itinerary = materialize_itinerary(
            candidate,
            context=context,
            catalog=catalog,
            assumptions=self._assumptions,
            day_themes=_composer_themes(self._composer, candidate, catalog),
        )
        return ItineraryDraftResult(
            success=True,
            itinerary=itinerary,
            candidate=candidate,
            composer_provider=type(self._composer).__name__,
        )

    def build_from_context(
        self, context: ItineraryBuildContext
    ) -> ItineraryBuildResult:
        draft = self.build_draft_from_context(context)
        if not draft.success or draft.candidate is None:
            return ItineraryBuildResult(
                success=False,
                validation=ItineraryValidationResult(
                    is_valid=False,
                    issues=[
                        ItineraryValidationIssue(
                            code="composition_failed",
                            message=draft.error_message or "draft build failed",
                        )
                    ],
                ),
            )

        catalog = build_grounded_catalog(
            context,
            indoor_types=self._assumptions.indoor_attraction_types,
        )
        catalog, _quality_stats = filter_catalog_quality(catalog)
        candidate_validation = validate_candidate(
            draft.candidate, context=context, catalog=catalog
        )
        if not candidate_validation.is_valid:
            return ItineraryBuildResult(
                success=False,
                candidate=draft.candidate,
                validation=candidate_validation,
                composer_provider=draft.composer_provider,
            )

        if draft.itinerary is None:
            return ItineraryBuildResult(
                success=False,
                candidate=draft.candidate,
                validation=candidate_validation,
                composer_provider=draft.composer_provider,
            )

        itinerary_validation = validate_itinerary(
            draft.itinerary,
            context=context,
            catalog=catalog,
        )
        if not itinerary_validation.is_valid:
            return ItineraryBuildResult(
                success=False,
                candidate=draft.candidate,
                validation=itinerary_validation,
                composer_provider=draft.composer_provider,
            )

        return ItineraryBuildResult(
            success=True,
            itinerary=draft.itinerary,
            candidate=draft.candidate,
            validation=ItineraryValidationResult(is_valid=True),
            composer_provider=draft.composer_provider,
        )


def _composer_themes(
    composer: ItineraryComposer,
    candidate: ItinerarySelectionCandidate,
    catalog: GroundedCatalog,
) -> dict[int, DayTheme]:
    last_themes = getattr(composer, "last_themes", None)
    if isinstance(last_themes, dict) and last_themes:
        return last_themes
    from app.itinerary.diversity.themes import derive_day_theme

    themes: dict[int, DayTheme] = {}
    for day in candidate.days:
        themes[day.day_number] = derive_day_theme(
            day.attraction_source_ids,
            catalog,
            used_titles={item.title for item in themes.values()},
        )
    return themes
