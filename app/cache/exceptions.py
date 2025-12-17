"""Custom cache exceptions."""


class CacheError(Exception):
    """Base class for cache exceptions."""


class CacheConnectionError(CacheError):
    """Raised when connection to cache fails."""
