"""Translates domain Specifications into SQLAlchemy WHERE clauses for Category.

This translator lives in the infrastructure layer: it is the only place
that knows about both the domain Specification hierarchy and the SQLAlchemy
ORM model.  The domain stays pure — Specification classes have no knowledge
of SQL.

Supported specifications
------------------------
* AllCategoriesSpecification        → no filter (returns all rows)
* ActiveCategorySpecification       → WHERE is_deleted = FALSE
* SlugMatchesSpecification          → WHERE slug = :slug
* NameContainsCategorySpecification → WHERE lower(name) LIKE '%keyword%'
* AndSpecification                  → left_clause AND right_clause
* OrSpecification                   → left_clause OR right_clause
* NotSpecification                  → NOT clause

Unsupported specification types raise ``NotImplementedError`` so that
missing coverage is immediately visible instead of silently falling back
to a full-table scan.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, false, not_, or_, true
from sqlalchemy import func as sql_func

from app.domain.model.example.category import Category
from app.domain.specifications.base import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)
from app.domain.specifications.category_specifications import (
    ActiveCategorySpecification,
    AllCategoriesSpecification,
    NameContainsCategorySpecification,
    SlugMatchesSpecification,
)
from app.infrastructure.persistence.sqlalchemy.models import CategoryORM


class CategorySpecificationTranslator:
    """Translates a ``Category`` Specification tree into a SQLAlchemy clause.

    Usage::

        clause = CategorySpecificationTranslator.translate(spec)
        stmt = select(CategoryORM).where(clause)
    """

    @classmethod
    def translate(cls, spec: Specification[Category]) -> ColumnElement[bool]:
        """Recursively translate *spec* into a SQLAlchemy boolean clause."""
        if isinstance(spec, AllCategoriesSpecification):
            return true()

        if isinstance(spec, ActiveCategorySpecification):
            return CategoryORM.is_deleted == false()  # type: ignore[return-value]

        if isinstance(spec, SlugMatchesSpecification):
            return CategoryORM.slug == spec.slug  # type: ignore[return-value]

        if isinstance(spec, NameContainsCategorySpecification):
            return sql_func.lower(CategoryORM.name).contains(spec.keyword)  # type: ignore[return-value]

        if isinstance(spec, AndSpecification):
            return and_(cls.translate(spec.left), cls.translate(spec.right))

        if isinstance(spec, OrSpecification):
            return or_(cls.translate(spec.left), cls.translate(spec.right))

        if isinstance(spec, NotSpecification):
            return not_(cls.translate(spec.spec))

        raise NotImplementedError(
            f"No SQL translation defined for Specification type: {type(spec).__name__}. "
            "Add a branch to CategorySpecificationTranslator.translate()."
        )
