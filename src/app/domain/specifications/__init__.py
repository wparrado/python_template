"""Domain specifications package.

Re-exports the Specification base and all concrete Item specifications
from a single import point for convenience.
"""

from app.domain.specifications.base import Specification
from app.domain.specifications.item_specifications import (
    ActiveItemSpecification,
    AllItemsSpecification,
    NameContainsSpecification,
    PriceInRangeSpecification,
)

__all__ = [
    "Specification",
    "ActiveItemSpecification",
    "AllItemsSpecification",
    "NameContainsSpecification",
    "PriceInRangeSpecification",
]
