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
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


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
        # Only one person can be "me".
        Index("one_me", "is_me", unique=True, postgresql_where=text("is_me")),
    )


def _person_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("persons.id", ondelete="CASCADE"), index=True)


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    person_a_id: Mapped[uuid.UUID] = _person_fk()
    person_b_id: Mapped[uuid.UUID] = _person_fk()
    type: Mapped[RelationshipType] = mapped_column(_pg_enum(RelationshipType, "relationship_type"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("person_a_id", "person_b_id", "type", name="uq_relationship"),
        CheckConstraint("person_a_id <> person_b_id", name="no_self_relationship"),
    )


class Fact(Base):
    """A labelled piece of information about a person, e.g. "Dog: Bamse"."""

    __tablename__ = "facts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = _person_fk()
    kind: Mapped[FactKind] = mapped_column(_pg_enum(FactKind, "fact_kind"), default=FactKind.TEXT)
    label: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Note(Base):
    """A dated free-text note about a person."""

    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = _person_fk()
    body: Mapped[str] = mapped_column(Text)
    happened_on: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
