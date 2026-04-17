"""PersistenceContainer — owns engine, session factory, health checks.

Centralises all decisions about the persistence backend so that the root
Container never imports SQLAlchemy or in-memory types directly.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.ports.health_check import IHealthCheck
from app.infrastructure.persistence.in_memory.category_repository import InMemoryCategoryRepository
from app.infrastructure.persistence.in_memory.health_check import InMemoryRepositoryHealthCheck
from app.infrastructure.persistence.in_memory.item_repository import InMemoryItemRepository
from app.infrastructure.persistence.sqlalchemy.health_check import SQLAlchemyHealthCheck
from app.settings import Settings


class PersistenceContainer:
    """Manages the persistence backend lifecycle.

    In SQLAlchemy mode an async engine and session factory are created once
    and shared for the lifetime of the process.  In memory mode two singleton
    repositories are kept instead — no connection management required.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        if settings.db_backend == "sqlalchemy":
            self._engine = create_async_engine(
                settings.database_url,
                echo=settings.debug,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
                pool_pre_ping=settings.db_pool_pre_ping,
            )
            self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
                self._engine, expire_on_commit=False
            )
            self._in_memory_item_repo: InMemoryItemRepository | None = None
            self._in_memory_category_repo: InMemoryCategoryRepository | None = None
        else:
            self._engine = None  # type: ignore[assignment]
            self._session_factory = None  # type: ignore[assignment]
            self._in_memory_item_repo = InMemoryItemRepository()
            self._in_memory_category_repo = InMemoryCategoryRepository()

    # ------------------------------------------------------------------
    # Accessors used by the root Container
    # ------------------------------------------------------------------

    @property
    def is_sqlalchemy(self) -> bool:
        """True when the SQLAlchemy backend is active."""
        return self._settings.db_backend == "sqlalchemy"

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the async session factory (SQLAlchemy mode only)."""
        assert self._session_factory is not None, "session_factory requires db_backend=sqlalchemy"
        return self._session_factory

    @property
    def in_memory_item_repo(self) -> InMemoryItemRepository:
        """Return the shared in-memory item repository (memory mode only)."""
        assert self._in_memory_item_repo is not None, "in_memory_item_repo requires db_backend=memory"
        return self._in_memory_item_repo

    @property
    def in_memory_category_repo(self) -> InMemoryCategoryRepository:
        """Return the shared in-memory category repository (memory mode only)."""
        assert self._in_memory_category_repo is not None, "in_memory_category_repo requires db_backend=memory"
        return self._in_memory_category_repo

    def health_checks(self) -> list[IHealthCheck]:
        """Return health check adapters for the active backend."""
        if self.is_sqlalchemy:
            return [SQLAlchemyHealthCheck(self._engine)]
        return [InMemoryRepositoryHealthCheck(self.in_memory_item_repo)]
