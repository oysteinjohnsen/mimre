"""Login in two steps: email + password, then a one-time code sent by email.

Error details are short machine-readable strings that the frontend translates.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy import delete, select

from app import auth
from app.config import settings
from app.deps import CurrentUser, DbDep, set_session_cookie
from app.email import Language, Mailer, get_mailer, login_code_email
from app.models import AuthSession, LoginChallenge, User

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

MAX_FAILED_LOGINS = 5  # wrong passwords before the account is locked for a while
LOCK_MINUTES = 15
CODE_MINUTES = 10
MAX_CODE_ATTEMPTS = 5
MAX_CODE_SENDS = 3
RESEND_COOLDOWN = timedelta(seconds=30)

MailerDep = Annotated[Mailer, Depends(get_mailer)]


class LoginRequest(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254)]
    password: Annotated[str, StringConstraints(max_length=1000)]
    language: Language = "nb"


class ChallengeResponse(BaseModel):
    challenge_id: uuid.UUID


class VerifyRequest(BaseModel):
    challenge_id: uuid.UUID
    code: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]


class ResendRequest(BaseModel):
    challenge_id: uuid.UUID
    language: Language = "nb"


class UserRead(BaseModel):
    id: uuid.UUID
    email: str


def _send_code(mailer: Mailer, user: User, code: str, language: Language) -> None:
    subject, body = login_code_email(code, language, CODE_MINUTES)
    try:
        mailer.send(user.email, subject, body)
    except Exception:
        log.exception("Sending login code failed")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "email_failed") from None


def _open_challenge(db: DbDep, challenge_id: uuid.UUID) -> LoginChallenge:
    challenge = db.get(LoginChallenge, challenge_id, with_for_update=True)
    if (
        challenge is None
        or challenge.consumed_at is not None
        or challenge.expires_at <= datetime.now(UTC)
        or challenge.attempts >= MAX_CODE_ATTEMPTS
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "challenge_expired")
    return challenge


@router.post("/login", response_model=ChallengeResponse)
def login(data: LoginRequest, db: DbDep, mailer: MailerDep) -> ChallengeResponse:
    """Step 1: check email and password, then email a one-time code."""
    now = datetime.now(UTC)
    user = db.scalar(select(User).where(User.email == data.email))

    if user is not None and user.locked_until is not None and user.locked_until > now:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "locked")

    # Unknown email and wrong password look the same (and take the same time).
    if not auth.verify_password(user.password_hash if user else None, data.password):
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED_LOGINS:
                user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                user.failed_logins = 0
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_credentials")

    assert user is not None
    user.failed_logins = 0
    user.locked_until = None
    if auth.needs_rehash(user.password_hash):
        user.password_hash = auth.hash_password(data.password)

    # Housekeeping: drop this user's old challenges and expired sessions.
    db.execute(delete(LoginChallenge).where(LoginChallenge.user_id == user.id))
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at <= now))

    code = auth.new_login_code()
    challenge = LoginChallenge(id=uuid.uuid4(), user_id=user.id, expires_at=now + timedelta(minutes=CODE_MINUTES))
    challenge.code_hash = auth.hash_login_code(challenge.id, code)
    db.add(challenge)
    db.commit()

    _send_code(mailer, user, code, data.language)
    return ChallengeResponse(challenge_id=challenge.id)


@router.post("/verify", response_model=UserRead)
def verify(data: VerifyRequest, request: Request, response: Response, db: DbDep) -> UserRead:
    """Step 2: check the emailed code and start a session (HttpOnly cookie)."""
    challenge = _open_challenge(db, data.challenge_id)
    now = datetime.now(UTC)

    if not auth.codes_match(challenge.code_hash, challenge.id, data.code):
        challenge.attempts += 1
        db.commit()
        detail = "challenge_expired" if challenge.attempts >= MAX_CODE_ATTEMPTS else "invalid_code"
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail)

    challenge.consumed_at = now
    user = db.get(User, challenge.user_id)
    assert user is not None
    user.last_login_at = now

    token = auth.new_session_token()
    db.add(
        AuthSession(
            token_hash=auth.hash_token(token),
            user_id=user.id,
            expires_at=now + timedelta(days=settings.session_days),
            last_seen_at=now,
            user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        )
    )
    db.commit()
    set_session_cookie(response, token)
    return UserRead(id=user.id, email=user.email)


@router.post("/resend", status_code=status.HTTP_204_NO_CONTENT)
def resend(data: ResendRequest, db: DbDep, mailer: MailerDep) -> None:
    """Send a new code for an open login (limited)."""
    challenge = _open_challenge(db, data.challenge_id)
    now = datetime.now(UTC)
    if challenge.sends >= MAX_CODE_SENDS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_codes")
    if challenge.last_sent_at > now - RESEND_COOLDOWN:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "resend_too_soon")

    code = auth.new_login_code()
    challenge.code_hash = auth.hash_login_code(challenge.id, code)
    challenge.expires_at = now + timedelta(minutes=CODE_MINUTES)
    challenge.attempts = 0
    challenge.sends += 1
    challenge.last_sent_at = now
    user = db.get(User, challenge.user_id)
    assert user is not None
    db.commit()
    _send_code(mailer, user, code, data.language)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbDep) -> None:
    token = request.cookies.get(auth.COOKIE_NAME)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == auth.hash_token(token)))
        db.commit()
    response.delete_cookie(auth.COOKIE_NAME, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax")


@router.get("/me", response_model=UserRead)
def current_user(user: CurrentUser) -> UserRead:
    return UserRead(id=user.id, email=user.email)
