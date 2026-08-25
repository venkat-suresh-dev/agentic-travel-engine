"""Flight tool errors."""


class FlightToolError(Exception):
    """Base flight tool error."""


class FlightValidationError(FlightToolError):
    """Raised when a flight search request is invalid."""


class AirportResolutionError(FlightToolError):
    """Raised when an origin or destination cannot be resolved to an airport code."""


class FlightProviderError(FlightToolError):
    """Raised when the upstream flight provider fails."""


class FlightProviderTimeoutError(FlightProviderError):
    """Raised when the upstream flight provider times out."""


class FlightRateLimitError(FlightProviderError):
    """Raised when the upstream flight provider rate-limits the request."""


class FlightNoDataError(FlightToolError):
    """Raised when the provider returns no flight offers."""


class FlightMalformedResponseError(FlightProviderError):
    """Raised when provider output cannot be parsed."""
