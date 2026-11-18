import calendar
import uuid
from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import FactKind, Gender

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
OptionalName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None


def validate_birthdate(year: int | None, month: int | None, day: int | None) -> None:
    """Raise ValueError if the (possibly partial) birthdate is impossible."""
    if day is not None and month is None:
        raise ValueError("birth_day requires birth_month")
    if year is not None and year > date.today().year:
        raise ValueError("birth_year cannot be in the future")
    if day is not None and month is not None:
        # Without a year, allow 29 Feb (it exists in leap years).
        max_day = calendar.monthrange(year if year is not None else 2000, month)[1]
        if day > max_day:
            raise ValueError("birth_day is not valid for this month")


class PersonBase(BaseModel):
    first_name: Name
    middle_name: OptionalName = None
    last_name: OptionalName = None
    nickname: OptionalName = None
    gender: Gender | None = None
    birth_year: int | None = Field(default=None, ge=1850)
    birth_month: int | None = Field(default=None, ge=1, le=12)
    birth_day: int | None = Field(default=None, ge=1, le=31)
    summary: str | None = None


class PersonCreate(PersonBase):
    """Also used for PUT /me (full replace of the user's own details)."""

    @model_validator(mode="after")
    def check_birthdate(self) -> Self:
        validate_birthdate(self.birth_year, self.birth_month, self.birth_day)
        return self


class PersonUpdate(BaseModel):
    """Partial update: only fields that are sent are changed. Send null to clear a field."""

    first_name: Name | None = None
    middle_name: OptionalName = None
    last_name: OptionalName = None
    nickname: OptionalName = None
    gender: Gender | None = None
    birth_year: int | None = Field(default=None, ge=1850)
    birth_month: int | None = Field(default=None, ge=1, le=12)
    birth_day: int | None = Field(default=None, ge=1, le=31)
    summary: str | None = None


class PersonRead(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_me: bool
    created_at: datetime
    updated_at: datetime


class PersonListItem(PersonRead):
    # When a search matched a fact or note rather than the name, a short excerpt of it.
    match: str | None = None


class PersonSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    middle_name: str | None
    last_name: str | None
    nickname: str | None
    gender: Gender | None
    is_me: bool


# --- Relationships ---------------------------------------------------------

# A relation as seen from one person: "the other person is my <relation>".
SymmetricRelation = Literal[
    "sibling", "spouse", "cohabitant", "partner", "ex", "friend", "colleague", "neighbor", "acquaintance", "cousin",
    "sibling_in_law",
]
DirectedRelation = Literal[
    "parent", "child", "grandparent", "grandchild", "aunt_uncle", "niece_nephew", "parent_in_law", "child_in_law"
]
Relation = DirectedRelation | SymmetricRelation


class RelationshipCreate(BaseModel):
    person_id: uuid.UUID
    other_id: uuid.UUID
    relation: Relation  # what other_id is to person_id

    @model_validator(mode="after")
    def check_distinct(self) -> Self:
        if self.person_id == self.other_id:
            raise ValueError("a person cannot be related to themselves")
        return self


class RelationshipRead(BaseModel):
    id: uuid.UUID | None  # None for inferred relationships (e.g. siblings via a shared parent)
    relation: Relation
    inferred: bool = False
    other: PersonSummary
    # For inferred relationships: the person it goes through (the shared parent, or the parent/child in between).
    via: PersonSummary | None = None


# --- Facts -----------------------------------------------------------------

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Value = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


def validate_fact_value(kind: FactKind, value: str) -> None:
    if kind == FactKind.DATE:
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError("date facts must be YYYY-MM-DD") from None
    elif kind == FactKind.EMAIL and "@" not in value:
        raise ValueError("not a valid email address")


class FactCreate(BaseModel):
    kind: FactKind = FactKind.TEXT
    label: Label
    value: Value

    @model_validator(mode="after")
    def check_value(self) -> Self:
        validate_fact_value(self.kind, self.value)
        return self


class FactUpdate(BaseModel):
    kind: FactKind | None = None
    label: Label | None = None
    value: Value | None = None


class FactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    kind: FactKind
    label: str
    value: str
    created_at: datetime
    updated_at: datetime


class FactLabel(BaseModel):
    label: str
    kind: FactKind


# --- Notes -----------------------------------------------------------------

Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class NoteCreate(BaseModel):
    body: Body
    happened_on: date | None = None  # defaults to today


class NoteUpdate(BaseModel):
    body: Body | None = None
    happened_on: date | None = None


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    body: str
    happened_on: date
    created_at: datetime
    updated_at: datetime
