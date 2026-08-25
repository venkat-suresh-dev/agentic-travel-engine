"""Distance tool errors."""


class DistanceToolError(Exception):
    """Base distance tool error."""


class DistanceValidationError(DistanceToolError):
    """Raised when a distance matrix request is invalid."""


class LocationResolutionError(DistanceToolError):
    """Raised when a location cannot be resolved to coordinates."""


class DistanceProviderError(DistanceToolError):
    """Raised when the upstream distance provider fails."""


class DistanceProviderTimeoutError(DistanceProviderError):
    """Raised when the upstream distance provider times out."""


class DistanceRateLimitError(DistanceProviderError):
    """Raised when the upstream distance provider rate-limits the request."""


class DistanceNoDataError(DistanceToolError):
    """Raised when the provider returns no route data."""


class DistanceMalformedResponseError(DistanceProviderError):
    """Raised when provider output cannot be parsed."""
