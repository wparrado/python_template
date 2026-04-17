"""Redirect — IUnitOfWork moved to the application layer.

The Unit of Work is an application-level orchestration pattern, not a
domain concept.  The domain only defines what it needs to persist
aggregates (``IItemRepository``) and publish events
(``IDomainEventPublisher``).

Import from the canonical location::

    from app.application.ports.unit_of_work import IUnitOfWork
"""
