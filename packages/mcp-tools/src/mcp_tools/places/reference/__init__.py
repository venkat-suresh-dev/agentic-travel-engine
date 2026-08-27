"""Free public reference sources for landmark discovery."""

from mcp_tools.places.reference.schemas import (
    LandmarkSearchRequest,
    LandmarkSearchResult,
    ReferenceLandmark,
    ReferenceLandmarkStatus,
)
from mcp_tools.places.reference.wikipedia import WikipediaLandmarkProvider

__all__ = [
    "LandmarkSearchRequest",
    "LandmarkSearchResult",
    "ReferenceLandmark",
    "ReferenceLandmarkStatus",
    "WikipediaLandmarkProvider",
]
