"""Contract tests for ICategoryRepository.

Any implementation of ICategoryRepository must pass these tests.
Add new adapters to the `repository` fixture to validate them.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.model.example.category import Category
from app.domain.ports.outbound.category_repository import ICategoryRepository
from app.domain.specifications.category_specifications import (
    ActiveCategorySpecification,
    NameContainsCategorySpecification,
    SlugMatchesSpecification,
)
from app.infrastructure.persistence.in_memory.category_repository import InMemoryCategoryRepository
from app.infrastructure.persistence.sqlalchemy.category_repository import SQLAlchemyCategoryRepository
from app.infrastructure.persistence.sqlalchemy.models import Base


@pytest.fixture(params=["in_memory", "sqlalchemy"])
async def repository(request: pytest.FixtureRequest) -> AsyncGenerator[ICategoryRepository, None]:
    """Parametrized fixture: add new adapters here to run the full contract."""
    if request.param == "in_memory":
        yield InMemoryCategoryRepository()
    elif request.param == "sqlalchemy":
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
        session = factory()
        try:
            yield SQLAlchemyCategoryRepository(session)
        finally:
            await session.close()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            await engine.dispose()
    else:
        raise ValueError(f"Unknown repository: {request.param}")


@pytest.mark.asyncio
async def test_save_and_find_by_id(repository: ICategoryRepository) -> None:
    cat = Category.create(name="Electronics", description="Electronic devices")
    await repository.save(cat)
    found = await repository.find_by_id(cat.id)
    assert found is not None
    assert found.id == cat.id
    assert found.name.value == "Electronics"


@pytest.mark.asyncio
async def test_find_by_id_returns_none_for_missing(repository: ICategoryRepository) -> None:
    result = await repository.find_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_find_by_slug(repository: ICategoryRepository) -> None:
    cat = Category.create(name="Home Appliances", slug="home-appliances")
    await repository.save(cat)
    found = await repository.find_by_slug("home-appliances")
    assert found is not None
    assert found.id == cat.id


@pytest.mark.asyncio
async def test_find_by_slug_returns_none_for_missing(repository: ICategoryRepository) -> None:
    result = await repository.find_by_slug("nonexistent-slug")
    assert result is None


@pytest.mark.asyncio
async def test_find_by_slug_excludes_deleted(repository: ICategoryRepository) -> None:
    cat = Category.create(name="Toys", slug="toys")
    cat.mark_deleted()
    await repository.save(cat)
    result = await repository.find_by_slug("toys")
    assert result is None


@pytest.mark.asyncio
async def test_find_all_returns_all_categories(repository: ICategoryRepository) -> None:
    cat1 = Category.create(name="Books", slug="books")
    cat2 = Category.create(name="Music", slug="music")
    await repository.save(cat1)
    await repository.save(cat2)
    all_cats = await repository.find_all()
    ids = {c.id for c in all_cats}
    assert cat1.id in ids
    assert cat2.id in ids


@pytest.mark.asyncio
async def test_find_all_pagination(repository: ICategoryRepository) -> None:
    for i in range(5):
        await repository.save(Category.create(name=f"Category {i}", slug=f"category-{i}"))
    page = await repository.find_all(limit=2, offset=1)
    assert len(page) == 2


@pytest.mark.asyncio
async def test_delete_removes_category(repository: ICategoryRepository) -> None:
    cat = Category.create(name="ToDelete", slug="to-delete")
    await repository.save(cat)
    await repository.delete(cat.id)
    assert await repository.find_by_id(cat.id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_is_noop(repository: ICategoryRepository) -> None:
    await repository.delete(uuid.uuid4())


@pytest.mark.asyncio
async def test_find_matching_by_name(repository: ICategoryRepository) -> None:
    electronics = Category.create(name="Electronics", slug="electronics")
    furniture = Category.create(name="Furniture", slug="furniture")
    await repository.save(electronics)
    await repository.save(furniture)

    results = await repository.find_matching(NameContainsCategorySpecification("elec"))

    assert len(results) == 1
    assert results[0].id == electronics.id


@pytest.mark.asyncio
async def test_find_matching_by_slug(repository: ICategoryRepository) -> None:
    cat = Category.create(name="Sports", slug="sports")
    await repository.save(cat)

    results = await repository.find_matching(SlugMatchesSpecification("sports"))

    assert len(results) == 1
    assert results[0].id == cat.id


@pytest.mark.asyncio
async def test_find_matching_active_categories(repository: ICategoryRepository) -> None:
    active = Category.create(name="Active Cat", slug="active-cat")
    deleted = Category.create(name="Deleted Cat", slug="deleted-cat")
    deleted.mark_deleted()
    await repository.save(active)
    await repository.save(deleted)

    results = await repository.find_matching(ActiveCategorySpecification())

    ids = {c.id for c in results}
    assert active.id in ids
    assert deleted.id not in ids


@pytest.mark.asyncio
async def test_find_matching_composite_spec(repository: ICategoryRepository) -> None:
    match = Category.create(name="Tech Electronics", slug="tech-electronics")
    no_match_name = Category.create(name="Furniture", slug="furniture")
    no_match_deleted = Category.create(name="Tech Deleted", slug="tech-deleted")
    no_match_deleted.mark_deleted()
    for cat in (match, no_match_name, no_match_deleted):
        await repository.save(cat)

    spec = ActiveCategorySpecification() & NameContainsCategorySpecification("tech")
    results = await repository.find_matching(spec)

    assert len(results) == 1
    assert results[0].id == match.id


@pytest.mark.asyncio
async def test_count_all(repository: ICategoryRepository) -> None:
    await repository.save(Category.create(name="Cat A", slug="cat-a"))
    await repository.save(Category.create(name="Cat B", slug="cat-b"))
    assert await repository.count() == 2


@pytest.mark.asyncio
async def test_count_with_spec(repository: ICategoryRepository) -> None:
    active = Category.create(name="Active", slug="active")
    deleted = Category.create(name="Deleted", slug="deleted")
    deleted.mark_deleted()
    await repository.save(active)
    await repository.save(deleted)

    count = await repository.count(ActiveCategorySpecification())
    assert count == 1
