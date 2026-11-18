"""person middle name

Revision ID: 2c3aa5315d9b
Revises: 3791122eb128
Create Date: 2026-11-18 20:45:26.042848
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '2c3aa5315d9b'
down_revision: str | None = '3791122eb128'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('persons', sa.Column('middle_name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('persons', 'middle_name')
