"""relationships facts notes

Revision ID: 092d4a71db17
Revises: 8c0323f12ab5
Create Date: 2026-11-18 19:38:49.921796
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '092d4a71db17'
down_revision: str | None = '8c0323f12ab5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Used by search: fuzzy name matching and accent-insensitive comparison.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.create_table('facts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.Enum('text', 'phone', 'email', 'address', 'url', 'date', name='fact_kind'), nullable=False),
    sa.Column('label', sa.String(length=100), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_facts_person_id'), 'facts', ['person_id'], unique=False)
    op.create_table('notes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('happened_on', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_person_id'), 'notes', ['person_id'], unique=False)
    op.create_table('relationships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('person_a_id', sa.Uuid(), nullable=False),
    sa.Column('person_b_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.Enum('parent', 'sibling', 'spouse', 'cohabitant', 'partner', 'ex', 'friend', 'colleague', 'neighbor', 'acquaintance', name='relationship_type'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('person_a_id <> person_b_id', name='no_self_relationship'),
    sa.ForeignKeyConstraint(['person_a_id'], ['persons.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['person_b_id'], ['persons.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('person_a_id', 'person_b_id', 'type', name='uq_relationship')
    )
    op.create_index(op.f('ix_relationships_person_a_id'), 'relationships', ['person_a_id'], unique=False)
    op.create_index(op.f('ix_relationships_person_b_id'), 'relationships', ['person_b_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_relationships_person_b_id'), table_name='relationships')
    op.drop_index(op.f('ix_relationships_person_a_id'), table_name='relationships')
    op.drop_table('relationships')
    op.drop_index(op.f('ix_notes_person_id'), table_name='notes')
    op.drop_table('notes')
    op.drop_index(op.f('ix_facts_person_id'), table_name='facts')
    op.drop_table('facts')
    for enum_name in ('relationship_type', 'fact_kind'):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
