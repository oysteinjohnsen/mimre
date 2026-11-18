"""create persons

Revision ID: 8c0323f12ab5
Revises: 
Create Date: 2026-11-18 18:08:52.165520
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '8c0323f12ab5'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('persons',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=True),
    sa.Column('nickname', sa.String(length=100), nullable=True),
    sa.Column('gender', sa.Enum('male', 'female', name='gender'), nullable=True),
    sa.Column('birth_year', sa.SmallInteger(), nullable=True),
    sa.Column('birth_month', sa.SmallInteger(), nullable=True),
    sa.Column('birth_day', sa.SmallInteger(), nullable=True),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('is_me', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('birth_day BETWEEN 1 AND 31', name='birth_day_range'),
    sa.CheckConstraint('birth_day IS NULL OR birth_month IS NOT NULL', name='birth_day_needs_month'),
    sa.CheckConstraint('birth_month BETWEEN 1 AND 12', name='birth_month_range'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('one_me', 'persons', ['is_me'], unique=True, postgresql_where=sa.text('is_me'))


def downgrade() -> None:
    op.drop_index('one_me', table_name='persons', postgresql_where=sa.text('is_me'))
    op.drop_table('persons')
    sa.Enum(name='gender').drop(op.get_bind(), checkfirst=True)
