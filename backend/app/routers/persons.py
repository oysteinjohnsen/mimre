import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Person
from app.schemas import PersonCreate, PersonRead, PersonUpdate, validate_birthdate

router = APIRouter(prefix="/persons", tags=["persons"])

SessionDep = Annotated[Session, Depends(get_session)]


def _get_or_404(session: Session, person_id: uuid.UUID) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person not found")
    return person


@router.get("", response_model=list[PersonRead])
def list_persons(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    include_me: bool = False,
) -> list[Person]:
    """List people. The user's own profile is excluded unless include_me=true."""
    stmt = select(Person)
    if not include_me:
        stmt = stmt.where(Person.is_me.is_(False))
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        full_name = func.concat_ws(" ", Person.first_name, Person.last_name)
        stmt = stmt.where(
            or_(full_name.ilike(pattern), Person.nickname.ilike(pattern))
        )
    stmt = stmt.order_by(func.lower(Person.first_name), func.lower(Person.last_name))
    return list(session.scalars(stmt))


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(data: PersonCreate, session: SessionDep) -> Person:
    person = Person(**data.model_dump())
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


@router.get("/{person_id}", response_model=PersonRead)
def get_person(person_id: uuid.UUID, session: SessionDep) -> Person:
    return _get_or_404(session, person_id)


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(person_id: uuid.UUID, data: PersonUpdate, session: SessionDep) -> Person:
    person = _get_or_404(session, person_id)
    changes = data.model_dump(exclude_unset=True)
    if "first_name" in changes and changes["first_name"] is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "first_name cannot be empty")

    merged = {f: changes.get(f, getattr(person, f)) for f in ("birth_year", "birth_month", "birth_day")}
    try:
        validate_birthdate(merged["birth_year"], merged["birth_month"], merged["birth_day"])
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    for field, value in changes.items():
        setattr(person, field, value)
    session.commit()
    session.refresh(person)
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: uuid.UUID, session: SessionDep) -> None:
    person = _get_or_404(session, person_id)
    session.delete(person)
    session.commit()
