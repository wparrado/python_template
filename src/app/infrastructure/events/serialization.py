"""Domain event serialization/deserialization utilities.

Converts DomainEvent dataclasses to/from JSON strings suitable for storage
in the outbox table.  Handles the standard field types used across all events:
uuid.UUID, datetime, Decimal, str, int, and their Optional variants.
"""

from __future__ import annotations

import dataclasses
import json
import types
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Union, get_args, get_origin, get_type_hints

from app.domain.events.base import DomainEvent
from app.infrastructure.events._registry import EVENT_REGISTRY


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _json_default(obj: Any) -> Any:
    """Encode types that are not natively JSON serializable."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize(event: DomainEvent) -> str:
    """Serialize a domain event to a JSON string."""
    return json.dumps(dataclasses.asdict(event), default=_json_default)


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------


def _is_optional(hint: Any) -> tuple[bool, Any]:
    """Return ``(True, inner_type)`` when *hint* is ``X | None`` or ``Optional[X]``."""
    origin = get_origin(hint)
    if origin in (Union, types.UnionType):
        args = get_args(hint)
        non_none = [a for a in args if a is not type(None)]
        if type(None) in args and len(non_none) == 1:
            return True, non_none[0]
    return False, hint


def _coerce(value: Any, hint: Any) -> Any:
    """Coerce a JSON-deserialized value to the annotated Python type."""
    is_opt, inner = _is_optional(hint)
    if is_opt:
        return None if value is None else _coerce(value, inner)
    if hint is uuid.UUID and isinstance(value, str):
        return uuid.UUID(value)
    if hint is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    if hint is Decimal and isinstance(value, (str, int, float)):
        return Decimal(str(value))
    return value


def deserialize(event_type: str, payload: str) -> DomainEvent:
    """Reconstruct a typed DomainEvent from its class name and JSON payload.

    Raises ``KeyError`` if *event_type* is not in the registry.
    """
    cls = EVENT_REGISTRY[event_type]
    raw: dict[str, Any] = json.loads(payload)
    hints = get_type_hints(cls)
    coerced = {key: _coerce(raw[key], hints[key]) for key in raw if key in hints}
    return cls(**coerced)
