"""Trip diversity, geographic clustering, and candidate selection."""

from app.itinerary.diversity.geography import GeographicRegion, cluster_attractions
from app.itinerary.diversity.quality import TripDiversityMetrics, assess_trip_diversity
from app.itinerary.diversity.selection import (
    TripUsageTracker,
    compose_diverse_itinerary,
    select_day_attractions,
    select_day_restaurant,
)
from app.itinerary.diversity.themes import DayTheme, derive_day_theme

__all__ = [
    "DayTheme",
    "GeographicRegion",
    "TripDiversityMetrics",
    "TripUsageTracker",
    "assess_trip_diversity",
    "cluster_attractions",
    "compose_diverse_itinerary",
    "derive_day_theme",
    "select_day_attractions",
    "select_day_restaurant",
]
