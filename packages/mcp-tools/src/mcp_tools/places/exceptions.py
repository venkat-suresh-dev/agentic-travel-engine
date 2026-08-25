"""Places tool errors."""


class PlacesToolError(Exception):
    """Base places tool error."""


class PlacesValidationError(PlacesToolError):
    """Raised when a places search request is invalid."""


class PlacesProviderError(PlacesToolError):
    """Raised when the upstream places provider fails."""


class PlacesProviderTimeoutError(PlacesProviderError):
    """Raised when the upstream places provider times out."""


class PlacesRateLimitError(PlacesProviderError):
    """Raised when the upstream places provider rate-limits the request."""


class PlacesNoDataError(PlacesToolError):
    """Raised when the provider returns no matching places."""


class PlacesMalformedResponseError(PlacesProviderError):
    """Raised when provider output cannot be parsed."""
