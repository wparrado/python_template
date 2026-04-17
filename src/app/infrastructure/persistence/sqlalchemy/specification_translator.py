"""Translates domain Specifications into SQLAlchemy WHERE clauses.

This translator lives in the infrastructure layer: it is the only place
that knows about both the domain Specification hierarchy and the SQLAlchemy
ORM model.  The domain stays pure — Specification classes have no knowledge
of SQL.

Supported specifications
------------------------
* AllItemsSpecification      → no filter (returns all rows)
* ActiveItemSpecification    → WHERE is_deleted = FALSE
* PriceInRangeSpecification  → WHERE price >= min AND/OR price <= max
* NameContainsSpecification  → WHERE lower(name) LIKE '%keyword%'
* AndSpecification           → left_clause AND right_clause
* OrSpecification            → left_clause OR right_clause
* NotSpecification           → NOT clause

Unsupported specification types raise ``NotImplementedError`` so that
missing coverage is immediately visible instead of silently falling back
to a full-table scan.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, false, not_, or_, true
from sqlalchemy import func as sql_func

from app.domain.model.example.item import Item
from app.domain.specifications.base import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)
from app.domain.specifications.item_specifications import (
    ActiveItemSpecification,
    AllItemsSpecification,
    NameContainsSpecification,
    PriceInRangeSpecification,
)
from app.infrastructure.persistence.sqlalchemy.models import ItemORM


class ItemSpecificationTranslator:
    """Translates an ``Item`` Specification tree into a SQLAlchemy clause.

    Usage::

        clause = ItemSpecificationTranslator.translate(spec)
        stmt = select(ItemORM).where(clause)
    """

    @classmethod
    def translate(cls, spec: Specification[Item]) -> ColumnElement[bool]:
        """Recursively translate *spec* into a SQLAlchemy boolean clause."""
        if isinstance(spec, AllItemsSpecification):
            return true()

        if isinstance(spec, ActiveItemSpecification):
            return ItemORM.is_deleted == false()

        if isinstance(spec, PriceInRangeSpecification):
            clauses: list[ColumnElement[bool]] = []
            if spec.min_price is not None:
                clauses.append(ItemORM.price >= spec.min_price)
            if spec.max_price is not None:
                clauses.append(ItemORM.price <= spec.max_price)
            return and_(*clauses) if clauses else true()

        if isinstance(spec, NameContainsSpecification):
            return sql_func.lower(ItemORM.name).contains(spec.keyword)

        if isinstance(spec, AndSpecification):
            return and_(cls.translate(spec.left), cls.translate(spec.right))

        if isinstance(spec, OrSpecification):
            return or_(cls.translate(spec.left), cls.translate(spec.right))

        if isinstance(spec, NotSpecification):
            return not_(cls.translate(spec.spec))

        raise NotImplementedError(
            f"No SQL translation defined for Specification type: {type(spec).__name__}. "
            "Add a branch to ItemSpecificationTranslator.translate()."
        )
