"""Distance provider abstractions."""

from __future__ import annotations

from typing import Protocol

from mcp_tools.distance.schemas import DistanceMatrixRequest, DistanceRoute


class DistanceProvider(Protocol):
    """Compute distance matrix routes from an upstream provider."""

    def get_distance_matrix(
        self, request: DistanceMatrixRequest
    ) -> list[DistanceRoute]: ...
