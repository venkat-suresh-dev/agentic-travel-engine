"""Travel-time estimation from distance tool data and deterministic fallbacks."""

from __future__ import annotations

import math
from dataclasses import dataclass

from mcp_tools.distance.schemas import DistanceDataStatus, DistanceMatrixResult

from app.budget.schemas import PriceDataKind
from app.itinerary.assumptions import SchedulingAssumptions


@dataclass(frozen=True, slots=True)
class TravelEstimate:
    distance_meters: int
    duration_seconds: int
    travel_mode: str
    source: str
    data_status: PriceDataKind


class TravelTimeEstimator:
    """Estimate travel using provider matrix routes or documented heuristics."""

    def __init__(
        self,
        distance_matrix: DistanceMatrixResult | None,
        assumptions: SchedulingAssumptions | None = None,
    ) -> None:
        self._matrix = distance_matrix
        self._assumptions = assumptions or SchedulingAssumptions()

    def estimate(
        self,
        *,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
    ) -> TravelEstimate:
        if (
            self._matrix is not None
            and self._matrix.data_status != DistanceDataStatus.UNAVAILABLE
        ):
            for route in self._matrix.routes:
                if (
                    _close(route.origin.latitude, origin_lat)
                    and _close(route.origin.longitude, origin_lng)
                    and _close(route.destination.latitude, destination_lat)
                    and _close(route.destination.longitude, destination_lng)
                ):
                    return TravelEstimate(
                        distance_meters=route.distance_meters,
                        duration_seconds=route.duration_seconds,
                        travel_mode=route.travel_mode.value,
                        source=self._matrix.source,
                        data_status=_distance_status(self._matrix.data_status.value),
                    )

        distance_meters = _haversine_meters(
            origin_lat, origin_lng, destination_lat, destination_lng
        )
        speed_kmh = float(self._assumptions.urban_driving_speed_kmh)
        duration_seconds = max(60, int((distance_meters / 1000.0 / speed_kmh) * 3600))
        return TravelEstimate(
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            travel_mode="driving",
            source="deterministic_haversine",
            data_status=PriceDataKind.ESTIMATED,
        )


def _distance_status(value: str) -> PriceDataKind:
    if value == "cached":
        return PriceDataKind.CACHED
    return PriceDataKind.LIVE


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(radius * c)


def _close(left: float, right: float, tolerance: float = 0.01) -> bool:
    return abs(left - right) <= tolerance
