"""Domain exceptions hierarchy.

All errors live in the domain layer.
Upper layers catch these and translate them to their own error types.
No external dependencies.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    """Raised when a domain invariant is violated."""


class NotFoundError(DomainError):
    """Raised when an aggregate or entity cannot be found."""


class ItemNotFoundError(NotFoundError):
    """Raised when a specific item cannot be found by ID."""

    def __init__(self, item_id: str) -> None:
        super().__init__(f"Item '{item_id}' not found")
        self.item_id = item_id


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state."""
