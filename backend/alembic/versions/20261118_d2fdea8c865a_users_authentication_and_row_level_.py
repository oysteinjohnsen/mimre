"""users, authentication and row-level security

- users, auth_sessions and login_challenges tables
- owner_id on all contact data (persons, relationships, facts, notes), defaulting to the
  logged-in user of the transaction (app.user_id)
- foreign keys that also require the same owner, so rows can't reference another user's people
- row-level security: each user only sees and writes their own rows
- a restricted login role for the app (name/password from DATABASE_URL); migrations keep
  running as the database owner

Existing data is given to an initial account "owner@mimre.local" that can't log in until
its email and password are set with the CLI (see README).

Revision ID: d2fdea8c865a
Revises: 2c3aa5315d9b
Create Date: 2026-11-18 23:30:00
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import make_url

from app.config import settings

revision: str = "d2fdea8c865a"
down_revision: str | None = "2c3aa5315d9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNED_TABLES = ("persons", "relationships", "facts", "notes")
CURRENT_USER_SQL = "NULLIF(current_setting('app.user_id', true), '')::uuid"
INITIAL_OWNER_EMAIL = "owner@mimre.local"


def _app_role() -> tuple[str, str]:
    url = make_url(settings.database_url)
    if not url.username or not url.password:
        raise RuntimeError("DATABASE_URL must include the app role's username and password")
    return url.username, url.password


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    bind = op.get_bind()
    role, password = _app_role()
    if role == bind.execute(sa.text("SELECT current_user")).scalar():
        raise RuntimeError("DATABASE_URL must use a separate role from ADMIN_DATABASE_URL (row-level security)")

    # --- Restricted app role (cluster-wide; created once, password kept in sync) ---------------
    exists = bind.execute(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}).scalar()
    verb = "ALTER" if exists else "CREATE"
    op.execute(
        f'{verb} ROLE "{role}" LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD {_quote_literal(password)}'
    )

    # --- Auth tables --------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("failed_logins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "login_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sends", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- Owner on all contact data --------------------------------------------------------------
    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("owner_id", sa.Uuid(), nullable=True))

    # Existing rows go to an initial account (unusable password '!' until set via the CLI).
    has_data = any(bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {t})")).scalar() for t in OWNED_TABLES)
    if has_data:
        owner_id = uuid.uuid4()
        bind.execute(
            sa.text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, '!')"),
            {"id": owner_id, "email": INITIAL_OWNER_EMAIL},
        )
        for table in OWNED_TABLES:
            bind.execute(sa.text(f"UPDATE {table} SET owner_id = :id"), {"id": owner_id})

    for table in OWNED_TABLES:
        op.alter_column(table, "owner_id", nullable=False, server_default=sa.text(CURRENT_USER_SQL))
        op.create_foreign_key(f"fk_{table}_owner", table, "users", ["owner_id"], ["id"], ondelete="CASCADE")
        op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])

    # One "me" per user instead of one in total.
    op.drop_index("one_me", table_name="persons", postgresql_where=sa.text("is_me"))
    op.create_index("one_me_per_owner", "persons", ["owner_id"], unique=True, postgresql_where=sa.text("is_me"))

    # References to people must stay within the same owner.
    op.create_unique_constraint("uq_persons_id_owner", "persons", ["id", "owner_id"])
    for table, column in (("relationships", "person_a_id"), ("relationships", "person_b_id"), ("facts", "person_id"), ("notes", "person_id")):
        op.drop_constraint(f"{table}_{column}_fkey", table, type_="foreignkey")
        op.create_foreign_key(
            f"fk_{column}_same_owner", table, "persons", [column, "owner_id"], ["id", "owner_id"], ondelete="CASCADE"
        )

    # --- Row-level security -----------------------------------------------------------------------
    for table in OWNED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY owner_only ON {table} USING (owner_id = {CURRENT_USER_SQL}) WITH CHECK (owner_id = {CURRENT_USER_SQL})"
        )

    # --- Privileges for the app role ------------------------------------------------------------
    op.execute(f'GRANT USAGE ON SCHEMA public TO "{role}"')
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{role}"')
    op.execute(f'REVOKE ALL ON alembic_version FROM "{role}"')
    # Tables created by later migrations get the same privileges (a test checks they also get RLS).
    op.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{role}"')


def downgrade() -> None:
    role, _ = _app_role()
    op.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM "{role}"')
    op.execute(f'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "{role}"')
    op.execute(f'REVOKE USAGE ON SCHEMA public FROM "{role}"')
    # The role itself is cluster-wide (shared with other databases), so it is not dropped.

    for table in OWNED_TABLES:
        op.execute(f"DROP POLICY owner_only ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table, column in (("relationships", "person_a_id"), ("relationships", "person_b_id"), ("facts", "person_id"), ("notes", "person_id")):
        op.drop_constraint(f"fk_{column}_same_owner", table, type_="foreignkey")
        op.create_foreign_key(f"{table}_{column}_fkey", table, "persons", [column], ["id"], ondelete="CASCADE")
    op.drop_constraint("uq_persons_id_owner", "persons", type_="unique")

    op.drop_index("one_me_per_owner", table_name="persons", postgresql_where=sa.text("is_me"))
    op.create_index("one_me", "persons", ["is_me"], unique=True, postgresql_where=sa.text("is_me"))

    for table in OWNED_TABLES:
        op.drop_index(f"ix_{table}_owner_id", table_name=table)
        op.drop_constraint(f"fk_{table}_owner", table, type_="foreignkey")
        op.drop_column(table, "owner_id")

    op.drop_table("login_challenges")
    op.drop_table("auth_sessions")
    op.drop_table("users")
