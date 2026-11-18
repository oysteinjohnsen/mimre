"""Test setup: API tests run against a separate `mimre_test` database, never the dev data.

The database is created (if missing) and migrated with Alembic once per test session,
and all tables are emptied after each test.
"""

import os

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+pg8000://mimre:mimre@localhost:5433/mimre_test")
# Must be set before the app is imported, since settings are read at import time.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def database() -> None:
    url = make_url(TEST_DATABASE_URL)
    assert url.database and url.database.endswith("_test"), "refusing to run tests against a non-test database"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        if not conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}):
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture
def client(database) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE persons, relationships, facts, notes CASCADE"))


@pytest.fixture
def make_person(client):
    """Create a person via the API and return its JSON."""

    def _make(first_name: str, **fields) -> dict:
        res = client.post("/api/persons", json={"first_name": first_name, **fields})
        assert res.status_code == 201, res.text
        return res.json()

    return _make
