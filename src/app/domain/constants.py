"""Domain-wide constants.

Pagination defaults and limits belong here so that domain ports
can reference them without creating a dependency on the application layer.
These values are also re-exported from ``app.application.constants`` for
backward-compatibility with the presentation layer.
"""

from __future__ import annotations

DEFAULT_PAGE_SIZE: int = 50
MAX_PAGE_SIZE: int = 1000
