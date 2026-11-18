"""Passwords, session tokens and login codes."""

import hashlib
import secrets
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

COOKIE_NAME = "mimre_session"
MIN_PASSWORD_LENGTH = 10

_hasher = PasswordHasher()  # Argon2id with the library's recommended parameters
# Verified against when the email is unknown, so both cases take the same time.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Only this hash is stored, so a database leak doesn't expose usable session tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def new_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_login_code(challenge_id: uuid.UUID, code: str) -> str:
    return hashlib.sha256(f"{challenge_id}:{code}".encode()).hexdigest()


def codes_match(stored_hash: str, challenge_id: uuid.UUID, code: str) -> bool:
    return secrets.compare_digest(stored_hash, hash_login_code(challenge_id, code))
