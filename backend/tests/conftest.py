"""Test setup.

API tests run against a separate `mimre_test` database (never the dev data), created and
migrated once per session. The app connects as the restricted role, exactly like in
production, so row-level security is active in every test. Login codes are captured by a
fake mailer instead of being emailed.

Fixtures:
- `client`: logged in as alice@example.com (most tests use this)
- `new_client()` + `login(client, email)`: more clients, e.g. a second user for isolation tests
- `anon_client`: not logged in
"""

import os

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+pg8000://mimre_app:mimre_app@localhost:5433/mimre_test")
TEST_ADMIN_DATABASE_URL = os.environ.get("TEST_ADMIN_DATABASE_URL", "postgresql+pg8000://mimre:mimre@localhost:5433/mimre_test")
# Must be set before the app is imported, since settings are read at import time.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ADMIN_DATABASE_URL"] = TEST_ADMIN_DATABASE_URL

import re  # noqa: E402
import uuid  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.email import get_mailer  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent
PASSWORD = "correct horse battery"
ALL_TABLES = "users, auth_sessions, login_challenges, persons, relationships, facts, notes"


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))

    def last_code(self, to: str) -> str:
        subject = next(s for t, s, _ in reversed(self.sent) if t == to)
        return re.search(r"\d{6}", subject).group()


@pytest.fixture(scope="session")
def database() -> None:
    for url in (TEST_DATABASE_URL, TEST_ADMIN_DATABASE_URL):
        assert make_url(url).database.endswith("_test"), "refusing to run tests against a non-test database"
    url = make_url(TEST_ADMIN_DATABASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}):
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def admin_engine(database) -> Engine:
    """Connects as the database owner (bypasses row-level security). For setup and assertions only."""
    return create_engine(TEST_ADMIN_DATABASE_URL)


@pytest.fixture
def mailer() -> Iterator[FakeMailer]:
    fake = FakeMailer()
    app.dependency_overrides[get_mailer] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_mailer, None)


@pytest.fixture
def new_client(admin_engine, mailer) -> Iterator:
    """Factory for independent clients (separate cookie jars). Empties the database afterwards."""
    clients: list[TestClient] = []

    def _new() -> TestClient:
        # https, so the Secure session cookie is sent back like in a real browser.
        c = TestClient(app, base_url="https://testserver")
        clients.append(c)
        return c

    yield _new
    for c in clients:
        c.close()
    with admin_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {ALL_TABLES} CASCADE"))


@pytest.fixture
def create_user(admin_engine):
    def _create(email: str, password: str = PASSWORD) -> uuid.UUID:
        with Session(admin_engine) as s:
            user = User(email=email, password_hash=hash_password(password))
            s.add(user)
            s.commit()
            return user.id

    return _create


@pytest.fixture
def login(mailer):
    """Log a client in through the real two-step flow."""

    def _login(client: TestClient, email: str, password: str = PASSWORD) -> TestClient:
        res = client.post("/api/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200, res.text
        res = client.post(
            "/api/auth/verify", json={"challenge_id": res.json()["challenge_id"], "code": mailer.last_code(email)}
        )
        assert res.status_code == 200, res.text
        return client

    return _login


@pytest.fixture
def anon_client(new_client) -> TestClient:
    return new_client()


@pytest.fixture
def client(new_client, create_user, login) -> TestClient:
    create_user("alice@example.com")
    return login(new_client(), "alice@example.com")


@pytest.fixture
def make_person(client):
    """Create a person via the API (as the logged-in `client` user) and return its JSON."""

    def _make(first_name: str, **fields) -> dict:
        res = client.post("/api/persons", json={"first_name": first_name, **fields})
        assert res.status_code == 201, res.text
        return res.json()

    return _make
