"""Authentication and authorization exceptions."""


class AuthenticationError(Exception):
    """Raised when a request is missing or has invalid authentication."""


class AuthorizationError(Exception):
    """Raised when an authenticated user lacks access to a resource."""


class ResourceNotFoundError(Exception):
    """Raised when an authenticated lookup cannot find a resource."""
