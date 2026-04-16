# Adding a Real Persistence Adapter

This template ships with an `InMemoryItemRepository` for demonstration.
To swap to a real database, follow these steps:

## 1. Create a new adapter module

```
infrastructure/
  persistence/
    sqlalchemy/               ← new adapter
      item_repository.py
      models.py               ← ORM models (SQLAlchemy declarative)
      session.py              ← async session factory
```

## 2. Implement `IItemRepository`

```python
from app.domain.ports.outbound.item_repository import IItemRepository
from app.domain.model.example.item import Item

class SqlAlchemyItemRepository(IItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, item: Item) -> None:
        orm_model = ItemOrmModel.from_domain(item)
        self._session.add(orm_model)
        await self._session.flush()

    async def find_by_id(self, item_id: uuid.UUID) -> Item | None:
        result = await self._session.get(ItemOrmModel, item_id)
        return result.to_domain() if result else None

    # ... implement find_all, delete
```

## 3. Wire in `container.py`

Replace `InMemoryItemRepository` with `SqlAlchemyItemRepository` in the DI container.

## 4. Update contract tests

`tests/integration/infrastructure/test_item_repository_contract.py` uses a
`pytest.fixture` parametrized over repository implementations.
Add your new adapter to the fixture to run the same contract tests.

## Domain stays unchanged

The `Item` aggregate and `IItemRepository` port never change.
Only the adapter and DI wiring change.
