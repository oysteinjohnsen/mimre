import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.deps import SessionDep, get_or_404, get_person_or_404
from app.models import Fact
from app.schemas import FactCreate, FactLabel, FactRead, FactUpdate, validate_fact_value

router = APIRouter(tags=["facts"])


@router.get("/persons/{person_id}/facts", response_model=list[FactRead])
def list_facts(person_id: uuid.UUID, session: SessionDep) -> list[Fact]:
    get_person_or_404(session, person_id)
    return list(session.scalars(select(Fact).where(Fact.person_id == person_id).order_by(Fact.created_at)))


@router.post("/persons/{person_id}/facts", response_model=FactRead, status_code=status.HTTP_201_CREATED)
def create_fact(person_id: uuid.UUID, data: FactCreate, session: SessionDep) -> Fact:
    get_person_or_404(session, person_id)
    fact = Fact(person_id=person_id, **data.model_dump())
    session.add(fact)
    session.commit()
    session.refresh(fact)
    return fact


@router.get("/facts/labels", response_model=list[FactLabel])
def list_labels(session: SessionDep) -> list[FactLabel]:
    """Labels already in use (most used first), each with its most common kind. Used for suggestions."""
    rows = session.execute(
        select(Fact.label, Fact.kind, func.count().label("n")).group_by(Fact.label, Fact.kind).order_by(func.count().desc())
    )
    result: dict[str, FactLabel] = {}
    for label, kind, _ in rows:
        result.setdefault(label, FactLabel(label=label, kind=kind))
    return list(result.values())


@router.patch("/facts/{fact_id}", response_model=FactRead)
def update_fact(fact_id: uuid.UUID, data: FactUpdate, session: SessionDep) -> Fact:
    fact = get_or_404(session, Fact, fact_id)
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    try:
        validate_fact_value(changes.get("kind", fact.kind), changes.get("value", fact.value))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    for field, value in changes.items():
        setattr(fact, field, value)
    session.commit()
    session.refresh(fact)
    return fact


@router.delete("/facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fact(fact_id: uuid.UUID, session: SessionDep) -> None:
    session.delete(get_or_404(session, Fact, fact_id))
    session.commit()
