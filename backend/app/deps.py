"""Request dependencies: who is logged in, and a database session acting on their behalf.

Endpoints for contact data use `SessionDep`. It requires a logged-in user (otherwise 401) and
returns a session limited by row-level security to that user's rows. There is deliberately no
way to get a contact-data session without a user.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, hash_token
from app.config import settings
from app.db import Base, get_session, user_session
from app.models import AuthSession, Person, User

# Unscoped session: only for authentication (users, sessions, login codes).
DbDep = Annotated[Session, Depends(get_session)]


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def get_current_user(request: Request, response: Response, db: DbDep) -> User:
    token = request.cookies.get(COOKIE_NAME)
    auth = db.get(AuthSession, hash_token(token)) if token else None
    now = datetime.now(UTC)
    if auth is None or auth.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")

    # Sliding expiry: extend the session (and cookie) at most once a day while it's being used.
    if auth.last_seen_at <= now - timedelta(days=1):
        auth.expires_at = now + timedelta(days=settings.session_days)
        set_session_cookie(response, token)
    auth.last_seen_at = now
    user = db.get(User, auth.user_id)
    db.commit()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_user_session(user: CurrentUser) -> Iterator[Session]:
    with user_session(user.id) as session:
        yield session


# Session for contact data, limited to the logged-in user's rows.
SessionDep = Annotated[Session, Depends(get_user_session)]


def get_or_404[T: Base](session: Session, model: type[T], id_: uuid.UUID) -> T:
    # Rows of other users are invisible (row-level security), so they also give 404.
    obj = session.get(model, id_)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj


def get_person_or_404(session: Session, person_id: uuid.UUID) -> Person:
    return get_or_404(session, Person, person_id)
