"""Weather tool errors."""


class WeatherToolError(Exception):
    """Base weather tool error."""


class WeatherValidationError(WeatherToolError):
    """Raised when a weather request is invalid."""


class GeocodingError(WeatherToolError):
    """Raised when a location cannot be resolved."""


class WeatherProviderError(WeatherToolError):
    """Raised when the upstream weather provider fails."""


class WeatherProviderTimeoutError(WeatherProviderError):
    """Raised when the upstream weather provider times out."""


class WeatherRateLimitError(WeatherProviderError):
    """Raised when the upstream weather provider rate-limits the request."""


class WeatherNoDataError(WeatherToolError):
    """Raised when the provider returns no forecast data."""


class WeatherMalformedResponseError(WeatherProviderError):
    """Raised when provider output cannot be parsed."""
