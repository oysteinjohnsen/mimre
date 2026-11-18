import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Gender(enum.StrEnum):
    MALE = "male"
    FEMALE = "female"


class Person(Base):
    """A person the user knows something about. The user is also a Person (is_me=True)."""

    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    nickname: Mapped[str | None] = mapped_column(String(100))
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, name="gender", values_callable=lambda e: [m.value for m in e])
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
