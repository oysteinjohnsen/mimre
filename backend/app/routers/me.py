"""The user's own profile: a Person with is_me=True, managed separately from other people."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import SessionDep
from app.models import Person
from app.schemas import PersonCreate, PersonRead

router = APIRouter(prefix="/me", tags=["me"])


def _get_me(session: Session) -> Person | None:
    return session.scalars(select(Person).where(Person.is_me.is_(True))).one_or_none()


@router.get("", response_model=PersonRead)
def get_me(session: SessionDep) -> Person:
    me = _get_me(session)
    if me is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not created yet")
    return me


@router.put("", response_model=PersonRead)
def put_me(data: PersonCreate, session: SessionDep, response: Response) -> Person:
    """Create the profile, or replace all its fields."""
    me = _get_me(session)
    if me is None:
        me = Person(is_me=True)
        session.add(me)
        response.status_code = status.HTTP_201_CREATED
    for field, value in data.model_dump().items():
        setattr(me, field, value)
    session.commit()
    session.refresh(me)
    return me
