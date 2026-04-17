"""SQLAlchemyCategoryUnitOfWork — removed, use SQLAlchemyUnitOfWork directly.

This module is kept as a compatibility shim.  The category-specific UoW was
identical to the item UoW except for the hardcoded repository.  Now that
``SQLAlchemyUnitOfWork`` accepts a ``repo_factory`` parameter it can serve
any aggregate, so the subclass is no longer needed.

Migrate any import of ``SQLAlchemyCategoryUnitOfWork`` to::

    from app.infrastructure.persistence.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWork
"""

from __future__ import annotations

# Re-export for any existing import that hasn't been migrated yet.
from app.infrastructure.persistence.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWork as SQLAlchemyCategoryUnitOfWork

__all__ = ["SQLAlchemyCategoryUnitOfWork"]
