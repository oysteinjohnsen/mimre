import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import ColumnElement, Text, cast, func, literal, or_, select
from sqlalchemy.orm import Session

from app.deps import SessionDep, get_person_or_404
from app.models import Fact, Note, Person
from app.schemas import PersonCreate, PersonListItem, PersonRead, PersonUpdate, validate_birthdate

router = APIRouter(prefix="/persons", tags=["persons"])

# Minimum pg_trgm word similarity for a fuzzy name match ("Ingird" -> "Ingrid").
NAME_SIMILARITY = 0.3


def _norm(expr) -> ColumnElement[str]:
    """Lowercase and strip accents, so "odegard" matches "Ødegård"."""
    return func.unaccent(func.lower(expr))


def _contains(haystack, needle) -> ColumnElement[bool]:
    return func.strpos(_norm(haystack), needle) > 0


def _snippet(text: str, term: str, width: int = 60) -> str:
    """A short excerpt of `text` around the first occurrence of `term`."""
    text = " ".join(text.split())
    if len(text) <= width:
        return text
    pos = max(text.lower().find(term.lower()), 0)
    start = max(pos - width // 3, 0)
    excerpt = text[start : start + width]
    return ("…" if start > 0 else "") + excerpt + ("…" if start + width < len(text) else "")


def _search(session: Session, term: str, include_me: bool) -> list[PersonListItem]:
    needle = _norm(cast(literal(term), Text))
    visible = Person.is_me.is_(False) if not include_me else literal(True)

    # (score, match excerpt) per person; name matches rank above fact/note matches.
    found: dict[uuid.UUID, tuple[float, str | None]] = {}

    name = _norm(func.concat_ws(" ", Person.first_name, Person.middle_name, Person.last_name, Person.nickname))
    similarity = func.word_similarity(needle, name)
    for person_id, exact, sim in session.execute(
        select(Person.id, func.strpos(name, needle) > 0, similarity).where(
            visible, or_(func.strpos(name, needle) > 0, similarity >= NAME_SIMILARITY)
        )
    ):
        found[person_id] = (2.0 if exact else 1.0 + sim, None)

    for person_id, label, value in session.execute(
        select(Fact.person_id, Fact.label, Fact.value)
        .join(Person)
        .where(visible, or_(_contains(Fact.value, needle), _contains(Fact.label, needle)))
        .order_by(Fact.created_at)
    ):
        found.setdefault(person_id, (0.5, f"{label}: {_snippet(value, term)}"))

    for person_id, body in session.execute(
        select(Note.person_id, Note.body).join(Person).where(visible, _contains(Note.body, needle)).order_by(Note.happened_on.desc())
    ):
        found.setdefault(person_id, (0.4, _snippet(body, term)))

    if not found:
        return []
    persons = session.scalars(select(Person).where(Person.id.in_(found)))
    items = [PersonListItem.model_validate(p).model_copy(update={"match": found[p.id][1]}) for p in persons]
    items.sort(key=lambda p: (-found[p.id][0], p.first_name.lower(), (p.last_name or "").lower()))
    return items


@router.get("", response_model=list[PersonListItem])
def list_persons(
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    include_me: bool = False,
) -> list[PersonListItem] | list[Person]:
    """List people, or search names (typo-tolerant), facts and notes with `q`.

    The user's own profile is excluded unless include_me=true.
    """
    if q and q.strip():
        return _search(session, q.strip(), include_me)
    stmt = select(Person)
    if not include_me:
        stmt = stmt.where(Person.is_me.is_(False))
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
    return get_person_or_404(session, person_id)


@router.patch("/{person_id}", response_model=PersonRead)
def update_person(person_id: uuid.UUID, data: PersonUpdate, session: SessionDep) -> Person:
    person = get_person_or_404(session, person_id)
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
    """Deletes the person along with their facts, notes and relationships."""
    session.delete(get_person_or_404(session, person_id))
    session.commit()
