"""Dependency Injection container — composition root.

Wires all ports to their adapter implementations by composing three
focused sub-containers:

* PersistenceContainer  — engine, session factory, repositories, health checks
* EventsContainer       — event broker, publishers, outbox relay
* ResilienceContainer   — circuit breaker

Change an adapter by editing the relevant sub-container without touching
any domain or application code.

Adding a new aggregate
----------------------
1. Create the domain model, ports, application handlers and service as usual.
2. Add one ``AggregateModule`` declaration in the relevant ``*_service_dependency``
   method — the generic ``_build_dep`` handles the rest.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.handlers.category_command_handlers import (
    CreateCategoryHandler,
    DeleteCategoryHandler,
    UpdateCategoryHandler,
)
from app.application.handlers.category_query_handlers import (
    GetCategoryHandler,
    ListCategoriesHandler,
    SearchCategoriesHandler,
)
from app.application.handlers.command_handlers import (
    CreateItemHandler,
    DeleteItemHandler,
    UpdateItemHandler,
)
from app.application.handlers.query_handlers import GetItemHandler, ListItemsHandler, SearchItemsHandler
from app.application.ports.category_application_service import ICategoryApplicationService
from app.application.ports.health_check import IHealthCheck
from app.application.ports.item_application_service import IItemApplicationService
from app.application.ports.unit_of_work import IUnitOfWork
from app.application.services.category_service import CategoryApplicationService, CategoryHandlers
from app.application.services.item_service import ItemApplicationService, ItemHandlers
from app.infrastructure.clock.system_clock import SystemClock
from app.infrastructure.di.events_container import EventsContainer
from app.infrastructure.di.persistence_container import PersistenceContainer
from app.infrastructure.di.resilience_container import ResilienceContainer
from app.infrastructure.events.broker.base import BrokerEventPublisher
from app.infrastructure.events.outbox_relay import OutboxRelay
from app.infrastructure.persistence.in_memory.category_unit_of_work import InMemoryCategoryUnitOfWork
from app.infrastructure.persistence.in_memory.unit_of_work import InMemoryUnitOfWork
from app.infrastructure.persistence.sqlalchemy.category_repository import SQLAlchemyCategoryRepository
from app.infrastructure.persistence.sqlalchemy.item_repository import SQLAlchemyItemRepository
from app.infrastructure.persistence.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWork
from app.infrastructure.resilience.pybreaker_adapter import PyBreakerAdapter
from app.settings import Settings


@dataclass
class AggregateModule[TService, THandlers]:
    """Wiring configuration for one aggregate service.

    Captures what *varies* between aggregates so that ``_build_dep`` can
    contain the single, shared lifecycle logic (session management, singleton
    for in-memory, per-request scope for SQLAlchemy).

    Fields
    ------
    repo_factory
        Callable that builds the read repository from an ``AsyncSession``.
        Used by both query handlers and — indirectly — the UoW.
    uow_factory
        Callable that builds a fresh ``IUnitOfWork`` from the session factory.
        Each command handler gets its own UoW to keep write transactions
        isolated from the shared read session.
    build_handlers
        Assembles the aggregate's handler group given a UoW (for commands)
        and a read repository (for queries).
    build_service
        Wraps the handler group in the application service.
    in_memory_repo
        The shared in-memory repository singleton (``None`` for SQLAlchemy mode).
    in_memory_uow
        Factory that builds an in-memory UoW from the given repository.
    """

    repo_factory: Callable[..., Any]
    uow_factory: Callable[[async_sessionmaker[AsyncSession]], IUnitOfWork[Any]]
    build_handlers: Callable[..., THandlers]
    build_service: Callable[[THandlers], TService]
    in_memory_repo: Any | None
    in_memory_uow: Callable[[Any], IUnitOfWork[Any]]


class Container:
    """Composition root — wires sub-containers into application services.

    Delegates infrastructure concerns to three focused sub-containers:

    * ``PersistenceContainer`` — engine, session factory, repositories, health checks
    * ``EventsContainer``      — event broker, publishers, outbox relay
    * ``ResilienceContainer``  — circuit breaker

    Adding a new aggregate requires only a new ``AggregateModule`` entry in
    the relevant ``*_service_dependency`` method; ``_build_dep`` handles the
    shared session-scoping lifecycle.
    """

    def __init__(self, settings: Settings) -> None:
        """Compose sub-containers and shared application-layer singletons."""
        self._persistence = PersistenceContainer(settings)
        self._events = EventsContainer(settings, self._persistence)
        self._resilience = ResilienceContainer(settings)
        self._clock = SystemClock()

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def circuit_breaker(self) -> PyBreakerAdapter:
        """Return the shared circuit breaker adapter."""
        return self._resilience.circuit_breaker()

    def broker(self) -> BrokerEventPublisher | None:
        """Return the configured broker adapter, or ``None`` for in-memory mode.

        The application lifespan must call ``broker.connect()`` on startup and
        ``broker.disconnect()`` on shutdown when this returns a non-None value.
        """
        return self._events.broker()

    def health_checks(self) -> list[IHealthCheck]:
        """Return all registered infrastructure health checks."""
        return self._persistence.health_checks()

    # ------------------------------------------------------------------
    # Application service dependencies — one session per HTTP request
    # ------------------------------------------------------------------

    def item_service_dependency(
        self,
    ) -> Callable[[], AsyncGenerator[IItemApplicationService, None]]:
        """Return an async generator function suitable for FastAPI ``Depends``.

        Session strategy
        ----------------
        Two distinct session scopes coexist per request intentionally:

        * **Read session** (query handlers):
          A single ``AsyncSession`` is shared by all SELECT operations.
          It is *never* used for writes.

        * **Write session** (command handlers via UoW):
          Each command handler opens its own ``AsyncSession`` scoped to its
          transactional boundary, keeping writes isolated from reads.
        """
        clock = self._clock

        def _build_item_handlers(uow: IUnitOfWork[Any], repo: Any) -> ItemHandlers:
            return ItemHandlers(
                create=CreateItemHandler(uow=uow, clock=clock),
                update=UpdateItemHandler(uow=uow, clock=clock),
                delete=DeleteItemHandler(uow=uow),
                get=GetItemHandler(repository=repo),
                list_all=ListItemsHandler(repository=repo),
                search=SearchItemsHandler(repository=repo),
            )

        return self._build_dep(
            AggregateModule(
                repo_factory=SQLAlchemyItemRepository,
                uow_factory=lambda sf: SQLAlchemyUnitOfWork(
                    session_factory=sf,
                    repo_factory=SQLAlchemyItemRepository,
                    publisher=self._events.in_process_publisher,
                    use_outbox=True,
                ),
                build_handlers=_build_item_handlers,
                build_service=lambda h: ItemApplicationService(handlers=h),
                in_memory_repo=self._persistence.in_memory_item_repo if not self._persistence.is_sqlalchemy else None,
                in_memory_uow=lambda r: InMemoryUnitOfWork(repository=r, publisher=self._events.in_process_publisher),
            )
        )

    def category_service_dependency(
        self,
    ) -> Callable[[], AsyncGenerator[ICategoryApplicationService, None]]:
        """Return an async generator function suitable for FastAPI ``Depends`` for Category.

        Follows the same session strategy as ``item_service_dependency``.
        """
        clock = self._clock

        def _build_category_handlers(uow: IUnitOfWork[Any], repo: Any) -> CategoryHandlers:
            return CategoryHandlers(
                create=CreateCategoryHandler(uow=uow),
                update=UpdateCategoryHandler(uow=uow, clock=clock),
                delete=DeleteCategoryHandler(uow=uow),
                get=GetCategoryHandler(repository=repo),
                list_all=ListCategoriesHandler(repository=repo),
                search=SearchCategoriesHandler(repository=repo),
            )

        return self._build_dep(
            AggregateModule(
                repo_factory=SQLAlchemyCategoryRepository,
                uow_factory=lambda sf: SQLAlchemyUnitOfWork(
                    session_factory=sf,
                    repo_factory=SQLAlchemyCategoryRepository,
                    publisher=self._events.in_process_publisher,
                    use_outbox=True,
                ),
                build_handlers=_build_category_handlers,
                build_service=lambda h: CategoryApplicationService(handlers=h),
                in_memory_repo=(
                    self._persistence.in_memory_category_repo if not self._persistence.is_sqlalchemy else None
                ),
                in_memory_uow=lambda r: InMemoryCategoryUnitOfWork(
                    repository=r, publisher=self._events.in_process_publisher
                ),
            )
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_dep[TService, THandlers](
        self,
        module: AggregateModule[TService, THandlers],
    ) -> Callable[[], AsyncGenerator[TService, None]]:
        """Single lifecycle factory for any aggregate service.

        * In-memory mode: builds the service once and yields the singleton on
          every request (safe — the in-memory store is not connection-bound).
        * SQLAlchemy mode: opens one ``AsyncSession`` per HTTP request for reads,
          builds a fresh service with per-request UoWs for writes, then releases
          the session automatically.
        """
        if not self._persistence.is_sqlalchemy:
            assert module.in_memory_repo is not None
            uow = module.in_memory_uow(module.in_memory_repo)
            singleton: TService = module.build_service(module.build_handlers(uow, module.in_memory_repo))

            async def _yield_singleton() -> AsyncGenerator[TService, None]:
                yield singleton

            return _yield_singleton

        session_factory = self._persistence.session_factory

        async def _request_scoped() -> AsyncGenerator[TService, None]:
            async with session_factory() as session:
                repo = module.repo_factory(session)
                uow = module.uow_factory(session_factory)
                yield module.build_service(module.build_handlers(uow, repo))

        return _request_scoped

    def outbox_relay(self) -> OutboxRelay | None:
        """Return an ``OutboxRelay`` if using the SQLAlchemy backend, else None.

        The relay polls the outbox table and forwards unpublished events to the
        configured downstream publisher (broker or in-process).
        The caller is responsible for calling ``start()`` / ``stop()``.
        """
        return self._events.outbox_relay()
