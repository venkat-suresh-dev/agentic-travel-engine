"""Currency tool errors."""


class CurrencyToolError(Exception):
    """Base currency tool error."""


class CurrencyValidationError(CurrencyToolError):
    """Raised when a currency conversion request is invalid."""


class CurrencyProviderError(CurrencyToolError):
    """Raised when the upstream currency provider fails."""


class CurrencyProviderTimeoutError(CurrencyProviderError):
    """Raised when the upstream currency provider times out."""


class CurrencyRateLimitError(CurrencyProviderError):
    """Raised when the upstream currency provider rate-limits the request."""


class CurrencyMalformedResponseError(CurrencyProviderError):
    """Raised when provider output cannot be parsed."""
