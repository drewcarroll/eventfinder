"""Domain-level exceptions.

These belong to the domain layer because they express violations of
business rules. They carry no knowledge of HTTP, databases, or any
external framework.
"""


class DomainError(Exception):
    """Base class for all domain errors."""


class InvalidValueError(DomainError):
    """Raised when a value object is constructed with an invalid value."""


class BusinessRuleViolation(DomainError):
    """Raised when an entity invariant or business rule is violated."""


class EntityNotFoundError(DomainError):
    """Raised when an entity cannot be located by its identity."""
