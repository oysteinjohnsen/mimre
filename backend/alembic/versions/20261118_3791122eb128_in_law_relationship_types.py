"""in-law relationship types

Revision ID: 3791122eb128
Revises: 83263507b86d
Create Date: 2026-11-18 20:40:03.907687
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '3791122eb128'
down_revision: str | None = '83263507b86d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NEW_VALUES = ("parent_in_law", "sibling_in_law")
OLD_VALUES = (
    "parent", "sibling", "spouse", "cohabitant", "partner", "ex", "friend", "colleague", "neighbor", "acquaintance",
    "grandparent", "aunt_uncle", "cousin",
)  # fmt: skip


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(f"ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres can't drop enum values: remove rows using them, then recreate the type.
    op.execute("DELETE FROM relationships WHERE type::text IN ('parent_in_law', 'sibling_in_law')")
    op.execute("ALTER TYPE relationship_type RENAME TO relationship_type_old")
    sa.Enum(*OLD_VALUES, name="relationship_type").create(op.get_bind())
    op.execute("ALTER TABLE relationships ALTER COLUMN type TYPE relationship_type USING type::text::relationship_type")
    op.execute("DROP TYPE relationship_type_old")
