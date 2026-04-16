"""Result[T, E] — typed return value for use-case handlers.

Errors do not cross layer boundaries as bare exceptions.
Each layer maps errors to its own types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


@dataclass(frozen=True)
class Success[T]:
    value: T

    @property
    def is_success(self) -> bool:
        return True

    @property
    def is_failure(self) -> bool:
        return False


@dataclass(frozen=True)
class Failure[E]:
    error: E

    @property
    def is_success(self) -> bool:
        return False

    @property
    def is_failure(self) -> bool:
        return True


type Result[T, E] = Success[T] | Failure[E]
