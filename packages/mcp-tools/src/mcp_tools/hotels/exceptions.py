"""Hotel tool errors."""


class HotelToolError(Exception):
    """Base hotel tool error."""


class HotelValidationError(HotelToolError):
    """Raised when a hotel search request is invalid."""


class CityResolutionError(HotelToolError):
    """Raised when a location cannot be resolved to a city code."""


class HotelProviderError(HotelToolError):
    """Raised when the upstream hotel provider fails."""


class HotelProviderTimeoutError(HotelProviderError):
    """Raised when the upstream hotel provider times out."""


class HotelRateLimitError(HotelProviderError):
    """Raised when the upstream hotel provider rate-limits the request."""


class HotelNoDataError(HotelToolError):
    """Raised when the provider returns no hotel offers."""


class HotelMalformedResponseError(HotelProviderError):
    """Raised when provider output cannot be parsed."""
