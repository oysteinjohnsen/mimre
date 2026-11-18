import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import Base, get_session
from app.models import Person

SessionDep = Annotated[Session, Depends(get_session)]


def get_or_404[T: Base](session: Session, model: type[T], id_: uuid.UUID) -> T:
    obj = session.get(model, id_)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj


def get_person_or_404(session: Session, person_id: uuid.UUID) -> Person:
    return get_or_404(session, Person, person_id)
