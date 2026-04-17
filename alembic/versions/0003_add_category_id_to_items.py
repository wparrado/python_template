"""Add category_id FK to items table.

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-01 00:00:02.000000

Adds an optional ``category_id`` foreign key to ``items`` so that each item
can be associated with at most one category.  The column is nullable so that
existing items and items created without a category remain valid.  Deletion
of a category sets ``category_id`` to NULL on all related items (SET NULL).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add category_id column and FK constraint to items."""
    op.add_column("items", sa.Column("category_id", sa.Uuid(), nullable=True))
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_foreign_key(
        "fk_items_category_id",
        "items",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove category_id column and FK constraint from items."""
    op.drop_constraint("fk_items_category_id", "items", type_="foreignkey")
    op.drop_index("ix_items_category_id", table_name="items")
    op.drop_column("items", "category_id")
