"""Itinerary critic package."""

from app.itinerary.critic.constants import MAX_ITINERARY_ATTEMPTS, MAX_ITINERARY_RETRIES
from app.itinerary.critic.schemas import (
    CriticIssue,
    CriticIssueCode,
    CriticIssueSeverity,
    CriticResult,
)

__all__ = [
    "CriticIssue",
    "CriticIssueCode",
    "CriticIssueSeverity",
    "CriticResult",
    "ItineraryCritic",
    "MAX_ITINERARY_ATTEMPTS",
    "MAX_ITINERARY_RETRIES",
]


def __getattr__(name: str) -> object:
    if name == "ItineraryCritic":
        from app.itinerary.critic.engine import ItineraryCritic

        return ItineraryCritic
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
