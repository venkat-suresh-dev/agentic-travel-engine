"""Deterministic diverse itinerary composer for production and tests."""

from __future__ import annotations

from app.itinerary.assumptions import SchedulingAssumptions
from app.itinerary.catalog import GroundedCatalog
from app.itinerary.context import ItineraryBuildContext
from app.itinerary.critic.schemas import CriticIssue, CriticIssueCode
from app.itinerary.diversity.selection import compose_diverse_itinerary
from app.itinerary.diversity.themes import DayTheme
from app.itinerary.schemas import ItinerarySelectionCandidate


class FakeItineraryComposer:
    """Select grounded attractions/restaurants with trip-wide diversity."""

    def __init__(self, assumptions: SchedulingAssumptions | None = None) -> None:
        self._assumptions = assumptions or SchedulingAssumptions()
        self._last_themes: dict[int, DayTheme] = {}

    @property
    def last_themes(self) -> dict[int, DayTheme]:
        return self._last_themes

    def compose(
        self,
        *,
        context: ItineraryBuildContext,
        catalog: GroundedCatalog,
    ) -> ItinerarySelectionCandidate:
        indoor_days = _indoor_override_days(context)
        candidate, themes = compose_diverse_itinerary(
            context=context,
            catalog=catalog,
            assumptions=self._assumptions,
            indoor_override_days=indoor_days,
        )
        self._last_themes = themes
        return candidate


def _indoor_override_days(context: ItineraryBuildContext) -> set[int]:
    grouped: dict[int, list[CriticIssue]] = {}
    for issue in context.critic_feedback:
        if issue.day_number is None:
            continue
        grouped.setdefault(issue.day_number, []).append(issue)
    return {
        day_number
        for day_number, issues in grouped.items()
        if any(issue.code == CriticIssueCode.WEATHER_RULE_VIOLATION for issue in issues)
    }
