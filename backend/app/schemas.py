import calendar
import uuid
from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import Gender

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
