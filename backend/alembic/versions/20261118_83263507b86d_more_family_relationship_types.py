"""more family relationship types

Revision ID: 83263507b86d
Revises: 092d4a71db17
Create Date: 2026-11-18 20:31:00.482708
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '83263507b86d'
down_revision: str | None = '092d4a71db17'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NEW_VALUES = ("grandparent", "aunt_uncle", "cousin")
OLD_VALUES = ("parent", "sibling", "spouse", "cohabitant", "partner", "ex", "friend", "colleague", "neighbor", "acquaintance")


def upgrade() -> None:
    for value in NEW_VALUES:
        op.execute(f"ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres can't drop enum values: remove rows using them, then recreate the type.
    op.execute("DELETE FROM relationships WHERE type::text IN ('grandparent', 'aunt_uncle', 'cousin')")
    op.execute("ALTER TYPE relationship_type RENAME TO relationship_type_old")
    sa.Enum(*OLD_VALUES, name="relationship_type").create(op.get_bind())
    op.execute("ALTER TABLE relationships ALTER COLUMN type TYPE relationship_type USING type::text::relationship_type")
    op.execute("DROP TYPE relationship_type_old")
