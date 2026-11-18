"""Database sessions.

Every transaction starts by telling Postgres who the logged-in user is (`app.user_id`).
Row-level security policies use it to show and accept only that user's rows, and it is
the default owner of new rows. Sessions without a user see no contact data at all.
"""

import uuid
from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@event.listens_for(SessionLocal, "after_begin")
def _set_current_user(session: Session, _transaction, connection) -> None:
    # Transaction-local (set_config(..., true)), so pooled connections never keep a previous user.
    connection.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": session.info.get("user_id", "")})


def get_session() -> Iterator[Session]:
    """A session with no logged-in user: only for authentication itself (users, sessions, login codes)."""
    with SessionLocal() as session:
        yield session


def user_session(user_id: uuid.UUID) -> Session:
    """A session acting on behalf of `user_id`; row-level security limits it to that user's data."""
    session = SessionLocal()
    session.info["user_id"] = str(user_id)
    return session
