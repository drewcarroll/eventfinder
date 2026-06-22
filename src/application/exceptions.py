"""Application-level exceptions.

Raised by use cases when an operation cannot complete. These are
translated into transport-specific responses by the interfaces layer.
"""


class ApplicationError(Exception):
    """Base class for application errors."""


class NotAuthorizedError(ApplicationError):
    """Raised when the caller lacks permission for an operation."""


class ResourceNotFoundError(ApplicationError):
    """Raised when a referenced resource does not exist."""


class ConflictError(ApplicationError):
    """Raised when an operation conflicts with existing state."""
