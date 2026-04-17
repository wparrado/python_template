"""Domain event consumers — inbound side of the message broker integration.

Each consumer adapter connects to a broker, subscribes to relevant topics /
queues, deserializes incoming messages back into typed ``DomainEvent`` objects,
and dispatches them to the registered ``InProcessEventPublisher`` handlers.

This is where a **second service** (e.g. a Notifications service, a Search
indexer, an Analytics service) would plug in to receive events produced by
this service.

Available adapters
------------------
- ``RabbitMQEventConsumer``  — subscribes to a queue bound to a topic exchange
- ``KafkaEventConsumer``     — subscribes to per-event Kafka topics

See ``base.py`` for the abstract interface.
"""

from app.infrastructure.events.consumer.base import BrokerEventConsumer

__all__ = ["BrokerEventConsumer"]
