# Domain Events & Transactional Outbox

This package contains the **event-publishing infrastructure** for the application.

---

## Architecture

```
Domain Layer
  └── DomainEvent (base class)          ← pure Python, no framework deps
  └── IDomainEventPublisher (port)       ← interface only

Application Layer
  └── commands / handlers               ← collect() events, hand to UoW

Infrastructure Layer (this package)
  ├── InProcessEventPublisher           ← dispatches to registered handlers in memory
  ├── OutboxEventPublisher              ← writes to outbox table (same transaction as aggregate)
  ├── OutboxRelay                       ← background worker: poll → dispatch → mark published
  ├── serialization.py                  ← DomainEvent ↔ JSON (handles UUID/datetime/Decimal)
  └── _registry.py                      ← maps event_type names back to domain classes
```

---

## Transactional Outbox Pattern

### The Problem

Sending a domain event to a message broker (Kafka, RabbitMQ, etc.) after a DB
commit creates a **dual-write** risk: the DB commit succeeds but the broker
publish fails → the event is silently lost.

### The Solution

Instead of publishing directly to the broker, the `SQLAlchemyUnitOfWork`
(when `use_outbox=True`) writes an `outbox` row **in the same transaction**
as the aggregate change.  This is atomic: either both land in the DB, or neither
does.

The `OutboxRelay` background worker then:
1. Queries `SELECT … WHERE published_at IS NULL … FOR UPDATE SKIP LOCKED`
2. Deserializes each event
3. Forwards it to the configured downstream publisher
4. Marks `published_at = now()`

Delivery guarantee: **at-least-once** (idempotent consumers recommended).

---

## Connecting a Real Broker

To forward events to Kafka, RabbitMQ, Redis Streams, etc., implement
`IDomainEventPublisher` and inject it into `OutboxRelay`:

```python
# src/app/infrastructure/events/kafka_publisher.py
from aiokafka import AIOKafkaProducer
from app.domain.events.base import DomainEvent
from app.domain.ports.outbound.event_publisher import IDomainEventPublisher
from app.infrastructure.events.serialization import serialize


class KafkaEventPublisher(IDomainEventPublisher):
    def __init__(self, producer: AIOKafkaProducer, topic: str) -> None:
        self._producer = producer
        self._topic = topic

    async def publish(self, event: DomainEvent) -> None:
        await self._producer.send_and_wait(
            self._topic,
            value=serialize(event).encode(),
            key=str(event.aggregate_id).encode(),
        )
```

Then wire it in `container.py`:

```python
def outbox_relay(self) -> OutboxRelay | None:
    if self._settings.db_backend != "sqlalchemy":
        return None
    broker_publisher = KafkaEventPublisher(producer=..., topic="domain-events")
    return OutboxRelay(
        session_factory=self._session_factory,
        publisher=broker_publisher,       # ← swap in your broker here
        poll_interval=self._settings.outbox_poll_interval_seconds,
    )
```

No changes to domain, application, or command handlers are required.

---

## Adding New Domain Events

1. Define the event in `src/app/domain/events/`:
   ```python
   @dataclass(frozen=True)
   class ItemShipped(DomainEvent):
       item_id: uuid.UUID
       destination: str
   ```

2. Register it in `_registry.py`:
   ```python
   from app.domain.events.item_events import ItemShipped

   EVENT_REGISTRY: dict[str, type[DomainEvent]] = {
       ...
       "ItemShipped": ItemShipped,
   }
   ```

3. Emit it from the aggregate, collect it in the handler — the outbox does the rest.

---

## Outbox Table Schema

| Column         | Type           | Notes                              |
|----------------|----------------|------------------------------------|
| `id`           | UUID (PK)      | Unique row identifier              |
| `event_type`   | VARCHAR        | Class name e.g. `"ItemCreated"`    |
| `aggregate_id` | UUID           | The aggregate root's identity      |
| `payload`      | TEXT (JSON)    | Full serialized event              |
| `created_at`   | TIMESTAMPTZ    | When the event was emitted (index) |
| `published_at` | TIMESTAMPTZ?   | NULL = unpublished (index)         |
