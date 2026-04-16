"""ValueObject base.

Value objects are immutable and compared by value, not identity.
They encapsulate validation of primitive types.
No external dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Base class for all value objects.

    Subclasses should be frozen dataclasses with ``frozen=True``.
    ``@dataclass(frozen=True)`` already generates correct ``__eq__`` and
    ``__hash__`` implementations based on all fields — no manual override
    is needed.  Use ``__post_init__`` to enforce invariants.
    """
