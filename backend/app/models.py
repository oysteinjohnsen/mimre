import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


# The logged-in user for the current transaction, set by app.db for every user-scoped session.
# Used as the default owner of new rows and by the row-level security policies (see migrations).
CURRENT_USER_SQL = "NULLIF(current_setting('app.user_id', true), '')::uuid"


def _owner_id() -> Mapped[uuid.UUID]:
    """Owner of a row. Filled in by the database from the logged-in user, never by application code."""
    return mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, server_default=text(CURRENT_USER_SQL)
    )


def _owned_person_fk(column: str) -> ForeignKeyConstraint:
    """Reference a person *of the same owner*, so rows can never point at another user's contacts."""
    return ForeignKeyConstraint(
        [column, "owner_id"], ["persons.id", "persons.owner_id"], ondelete="CASCADE", name=f"fk_{column}_same_owner"
    )


# --- Users and authentication ------------------------------------------------------------------


class User(Base):
    """An account. Created with the CLI (`python -m app.cli create-user`), there is no public sign-up."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-cased
    password_hash: Mapped[str] = mapped_column(String(255))
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    """A logged-in device. The cookie holds a random token; only its SHA-256 hash is stored."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginChallenge(Base):
    """Second login step: a one-time code sent by email after a correct password."""

    __tablename__ = "login_challenges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    sends: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Contact data (all owned by a user, protected by row-level security) ---------------------


def _pg_enum(cls: type[enum.Enum], name: str) -> Enum:
    """Postgres enum stored by value (e.g. 'male'), not by Python member name."""
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class Gender(enum.StrEnum):
    MALE = "male"
    FEMALE = "female"


class RelationshipType(enum.StrEnum):
    """How two people are related, stored once per pair.

    PARENT, GRANDPARENT, AUNT_UNCLE and PARENT_IN_LAW are directed: person_a is the parent /
    grandparent / aunt or uncle / parent-in-law of person_b. All other types are symmetric and stored with
    person_a_id < person_b_id so each pair exists once.
    """

    PARENT = "parent"
    SIBLING = "sibling"
    SPOUSE = "spouse"
    COHABITANT = "cohabitant"
    PARTNER = "partner"
    EX = "ex"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    NEIGHBOR = "neighbor"
    ACQUAINTANCE = "acquaintance"
    GRANDPARENT = "grandparent"
    AUNT_UNCLE = "aunt_uncle"
    COUSIN = "cousin"
    PARENT_IN_LAW = "parent_in_law"
    SIBLING_IN_LAW = "sibling_in_law"


class FactKind(enum.StrEnum):
    """Decides how a fact's value is validated and displayed (e.g. phone -> tel: link)."""

    TEXT = "text"
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"
    URL = "url"
    DATE = "date"


class Person(Base):
    """A person the user knows something about. The user is also a Person (is_me=True)."""

    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = _owner_id()
    first_name: Mapped[str] = mapped_column(String(100))
    middle_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    nickname: Mapped[str | None] = mapped_column(String(100))
    gender: Mapped[Gender | None] = mapped_column(
        _pg_enum(Gender, "gender")
    )

    # Birthdate is stored in parts because we often only know some of it
    # (e.g. "born 2019" or "birthday 14 March").
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    birth_month: Mapped[int | None] = mapped_column(SmallInteger)
    birth_day: Mapped[int | None] = mapped_column(SmallInteger)

    summary: Mapped[str | None] = mapped_column(Text)
    is_me: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("birth_month BETWEEN 1 AND 12", name="birth_month_range"),
        CheckConstraint("birth_day BETWEEN 1 AND 31", name="birth_day_range"),
        CheckConstraint("birth_day IS NULL OR birth_month IS NOT NULL", name="birth_day_needs_month"),
        # Each user has at most one "me" (their profile).
        Index("one_me_per_owner", "owner_id", unique=True, postgresql_where=text("is_me")),
        # Target for the same-owner foreign keys from relationships, facts and notes.
        UniqueConstraint("id", "owner_id", name="uq_persons_id_owner"),
    )


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = _owner_id()
    person_a_id: Mapped[uuid.UUID] = mapped_column(index=True)
    person_b_id: Mapped[uuid.UUID] = mapped_column(index=True)
    type: Mapped[RelationshipType] = mapped_column(_pg_enum(RelationshipType, "relationship_type"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("person_a_id", "person_b_id", "type", name="uq_relationship"),
        CheckConstraint("person_a_id <> person_b_id", name="no_self_relationship"),
        _owned_person_fk("person_a_id"),
        _owned_person_fk("person_b_id"),
    )


class Fact(Base):
    """A labelled piece of information about a person, e.g. "Dog: Bamse"."""

    __tablename__ = "facts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = _owner_id()
    person_id: Mapped[uuid.UUID] = mapped_column(index=True)
    kind: Mapped[FactKind] = mapped_column(_pg_enum(FactKind, "fact_kind"), default=FactKind.TEXT)
    label: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (_owned_person_fk("person_id"),)


class Note(Base):
    """A dated free-text note about a person."""

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = _owner_id()
    person_id: Mapped[uuid.UUID] = mapped_column(index=True)
    body: Mapped[str] = mapped_column(Text)
    happened_on: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (_owned_person_fk("person_id"),)
