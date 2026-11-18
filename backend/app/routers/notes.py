import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import SessionDep, get_or_404, get_person_or_404
from app.models import Note
from app.schemas import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(tags=["notes"])


@router.get("/persons/{person_id}/notes", response_model=list[NoteRead])
def list_notes(person_id: uuid.UUID, session: SessionDep) -> list[Note]:
    get_person_or_404(session, person_id)
    stmt = select(Note).where(Note.person_id == person_id).order_by(Note.happened_on.desc(), Note.created_at.desc())
    return list(session.scalars(stmt))


@router.post("/persons/{person_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(person_id: uuid.UUID, data: NoteCreate, session: SessionDep) -> Note:
    get_person_or_404(session, person_id)
    note = Note(person_id=person_id, body=data.body)
    if data.happened_on is not None:
        note.happened_on = data.happened_on
    session.add(note)
    session.commit()
    session.refresh(note)
    return note


@router.patch("/notes/{note_id}", response_model=NoteRead)
def update_note(note_id: uuid.UUID, data: NoteUpdate, session: SessionDep) -> Note:
    note = get_or_404(session, Note, note_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(note, field, value)
    session.commit()
    session.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: uuid.UUID, session: SessionDep) -> None:
    session.delete(get_or_404(session, Note, note_id))
    session.commit()
