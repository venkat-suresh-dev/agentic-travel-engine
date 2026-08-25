"""Distance tool application boundary."""

from __future__ import annotations

from mcp_tools.distance.schemas import (
    DistanceMatrixRequest,
    DistanceMatrixResult,
    DistanceToolMetadata,
)
from mcp_tools.distance.service import DistanceService


class DistanceTool:
    """Invoke the MCP-backed distance matrix capability from the application layer."""

    def __init__(self, distance_service: DistanceService | None = None) -> None:
        if distance_service is None:
            msg = "distance_service is required"
            raise ValueError(msg)
        self._distance_service = distance_service

    @property
    def distance_service(self) -> DistanceService:
        return self._distance_service

    def get_distance_matrix(
        self,
        request: DistanceMatrixRequest,
    ) -> tuple[DistanceMatrixResult, DistanceToolMetadata]:
        """Fetch normalized distance matrix results with provenance metadata."""
        result, metadata = self._distance_service.get_distance_matrix(request)
        return result, metadata
