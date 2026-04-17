"""Message broker adapters for domain event publishing.

Each adapter implements ``IDomainEventPublisher`` so the rest of the system
(domain, application) is completely unaware of which broker is in use.

Available adapters
------------------
- ``InProcessEventPublisher``  — in-memory, no broker required (default / testing)
- ``RabbitMQEventPublisher``   — AMQP topic exchange via *aio-pika*
- ``KafkaEventPublisher``      — per-event topics via *aiokafka*

Adapters that need a network connection extend ``BrokerEventPublisher`` and
expose ``connect()`` / ``disconnect()`` lifecycle methods.  The application
factory is responsible for calling those during startup and shutdown.
"""

from app.infrastructure.events.broker.base import BrokerEventPublisher

__all__ = ["BrokerEventPublisher"]
