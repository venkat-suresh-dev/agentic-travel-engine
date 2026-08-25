"""Selective trip modification package."""

from app.modification.schemas import (
    ModificationFailure,
    ModificationIntent,
    ModificationScope,
    ModificationStatus,
    RefreshPlan,
    TripModificationRequest,
)

__all__ = [
    "ModificationEngine",
    "ModificationFailure",
    "ModificationIntent",
    "ModificationScope",
    "ModificationStatus",
    "RefreshPlan",
    "TripModificationRequest",
    "is_completed_plan_modification",
]


def __getattr__(name: str) -> object:
    if name == "ModificationEngine":
        from app.modification.engine import ModificationEngine

        return ModificationEngine
    if name == "is_completed_plan_modification":
        from app.modification.detector import is_completed_plan_modification

        return is_completed_plan_modification
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
