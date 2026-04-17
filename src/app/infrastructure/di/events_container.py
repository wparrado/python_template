"""EventsContainer — owns event publishers, broker and outbox relay.

Centralises all decisions about event delivery so the root Container
never imports broker or relay types directly.
"""

from __future__ import annotations

from app.domain.ports.outbound.event_publisher import IDomainEventPublisher
from app.infrastructure.di.persistence_container import PersistenceContainer
from app.infrastructure.events.broker.base import BrokerEventPublisher
from app.infrastructure.events.broker.kafka import KafkaEventPublisher
from app.infrastructure.events.broker.rabbitmq import RabbitMQEventPublisher
from app.infrastructure.events.in_process_publisher import InProcessEventPublisher
from app.infrastructure.events.outbox_relay import OutboxRelay
from app.settings import Settings


class EventsContainer:
    """Manages event publisher and outbox relay lifecycle.

    Three delivery modes are supported via ``settings.event_broker``:

    * ``'memory'``   — in-process only; no external broker needed.
    * ``'rabbitmq'`` — relay forwards events to a RabbitMQ topic exchange.
    * ``'kafka'``    — relay forwards events to Kafka topics.

    The ``OutboxRelay`` is only instantiated when using the SQLAlchemy backend;
    the in-memory backend dispatches events synchronously inside the UoW.
    """

    def __init__(self, settings: Settings, persistence: PersistenceContainer) -> None:
        self._settings = settings
        self._persistence = persistence

        # Always present — used by UoW and as fallback in memory mode.
        self._in_process_publisher = InProcessEventPublisher()

        # Optional downstream broker (None in memory mode).
        self._broker: BrokerEventPublisher | None = self._build_broker(settings)

        # The relay publisher: broker when configured, otherwise in-process.
        self._relay_publisher: IDomainEventPublisher = (
            self._broker if self._broker is not None else self._in_process_publisher
        )

    # ------------------------------------------------------------------
    # Accessors used by the root Container
    # ------------------------------------------------------------------

    @property
    def in_process_publisher(self) -> InProcessEventPublisher:
        """Return the shared in-process event publisher."""
        return self._in_process_publisher

    def broker(self) -> BrokerEventPublisher | None:
        """Return the configured broker adapter, or ``None`` for in-memory mode.

        The application lifespan must call ``broker.connect()`` on startup and
        ``broker.disconnect()`` on shutdown when this returns a non-None value.
        """
        return self._broker

    def outbox_relay(self) -> OutboxRelay | None:
        """Return an ``OutboxRelay`` if using the SQLAlchemy backend, else None.

        The relay polls the outbox table and forwards unpublished events to the
        configured downstream publisher.  The caller is responsible for calling
        ``start()`` / ``stop()``.
        """
        if not self._persistence.is_sqlalchemy:
            return None
        return OutboxRelay(
            session_factory=self._persistence.session_factory,
            publisher=self._relay_publisher,
            poll_interval=self._settings.outbox_poll_interval_seconds,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_broker(settings: Settings) -> BrokerEventPublisher | None:
        """Instantiate the configured broker adapter (without connecting).

        Returns ``None`` when ``event_broker='memory'`` — no external broker
        needed.  The returned adapter must be connected by the caller before use.
        """
        if settings.event_broker == "rabbitmq":
            return RabbitMQEventPublisher(
                url=settings.rabbitmq_url,
                exchange_name=settings.rabbitmq_exchange,
            )
        if settings.event_broker == "kafka":
            return KafkaEventPublisher(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                topic_prefix=settings.kafka_topic_prefix,
            )
        return None
