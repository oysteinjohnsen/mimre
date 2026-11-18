"""Security guard rails. These protect future features too:

- every API endpoint (except logging in) must require a logged-in user
- every table must have row-level security (or be explicitly listed as an auth table)
- the app's database role must not be able to bypass row-level security
- one user can never see, change, search or link another user's data
"""

import re
import uuid

import pytest
from sqlalchemy import create_engine, text

from app.main import app
from tests.conftest import TEST_DATABASE_URL

PUBLIC_ENDPOINTS = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/verify"),
    ("POST", "/api/auth/resend"),
    ("POST", "/api/auth/logout"),
}

# Tables without row-level security. Only authentication tables, which are read before anyone is
# logged in. Anything else added here needs a very good reason.
TABLES_WITHOUT_RLS = {"users", "auth_sessions", "login_challenges", "alembic_version"}


def api_routes() -> set[tuple[str, str]]:
    """All API endpoints, read from the OpenAPI schema (FastAPI's public description of the routes)."""
    paths = app.openapi()["paths"]
    return {(method.upper(), path) for path, ops in paths.items() for method in ops if path.startswith("/api/")}


def test_endpoint_discovery_works():
    # Guards the guard: if discovery breaks, the login test below must not silently test nothing.
    routes = api_routes()
    assert len(routes) >= 20
    assert PUBLIC_ENDPOINTS <= routes


@pytest.mark.parametrize(("method", "path"), sorted(api_routes() - PUBLIC_ENDPOINTS))
def test_every_endpoint_requires_login(anon_client, method, path):
    url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
    res = anon_client.request(method, url, json={} if method in ("POST", "PUT", "PATCH") else None)
    assert res.status_code == 401, f"{method} {path} answered {res.status_code} without login"


def test_every_table_has_row_level_security(admin_engine):
    with admin_engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT c.relname, c.relrowsecurity, count(p.polname)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                LEFT JOIN pg_policy p ON p.polrelid = c.oid
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                GROUP BY c.relname, c.relrowsecurity
            """)
        ).all()
    missing = [name for name, rls, policies in rows if name not in TABLES_WITHOUT_RLS and not (rls and policies)]
    assert not missing, f"tables without row-level security policies: {missing}"


def test_app_role_cannot_bypass_rls(admin_engine):
    role = re.match(r".*://([^:]+):", TEST_DATABASE_URL).group(1)
    with admin_engine.connect() as conn:
        superuser, bypass = conn.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = :r"), {"r": role}).one()
    assert not superuser and not bypass


def test_database_hides_rows_without_a_logged_in_user(make_person):
    make_person("Kari")
    engine = create_engine(TEST_DATABASE_URL)  # the app's role, with no app.user_id set
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM persons")) == 0
    engine.dispose()


def test_database_rejects_rows_for_another_owner(client, admin_engine, create_user):
    """Even with a bug in the app, the database refuses to write rows owned by someone else."""
    other = create_user("mallory@example.com")
    engine = create_engine(TEST_DATABASE_URL)
    alice = client.get("/api/auth/me").json()["id"]
    with engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": alice})
        with pytest.raises(Exception, match="row-level security"):
            conn.execute(text("INSERT INTO persons (id, owner_id, first_name) VALUES (:id, :o, 'X')"), {"id": uuid.uuid4(), "o": other})
        conn.rollback()
    engine.dispose()


def test_database_rejects_references_across_owners(make_person, admin_engine, create_user):
    """Facts/notes/relationships must point at a person with the same owner (checked by foreign keys)."""
    kari = make_person("Kari")
    other = create_user("mallory@example.com")
    with admin_engine.connect() as conn, pytest.raises(Exception, match="fk_person_id_same_owner"):
        conn.execute(
            text("INSERT INTO facts (id, owner_id, person_id, kind, label, value) VALUES (:id, :o, :p, 'text', 'x', 'y')"),
            {"id": uuid.uuid4(), "o": other, "p": kari["id"]},
        )


@pytest.fixture
def two_users(client, make_person, new_client, create_user, login):
    """Alice (the default client) with some data, and Bob logged in separately."""
    kari = make_person("Kari", last_name="Nordmann")
    lars = make_person("Lars")
    fact = client.post(f"/api/persons/{kari['id']}/facts", json={"label": "Hund", "value": "Bamse"}).json()
    note = client.post(f"/api/persons/{kari['id']}/notes", json={"body": "Hemmelig notat om Lofoten"}).json()
    rel = client.post("/api/relationships", json={"person_id": lars["id"], "other_id": kari["id"], "relation": "parent"}).json()
    client.put("/api/me", json={"first_name": "Alice"})

    create_user("bob@example.com")
    bob = login(new_client(), "bob@example.com")
    return {"alice": client, "bob": bob, "kari": kari, "lars": lars, "fact": fact, "note": note, "rel": rel}


def test_other_users_data_is_invisible(two_users):
    bob, kari = two_users["bob"], two_users["kari"]
    assert bob.get("/api/persons").json() == []
    assert bob.get("/api/persons", params={"include_me": "true"}).json() == []
    for q in ("Kari", "Nordmann", "Bamse", "Lofoten"):  # names, facts and notes
        assert bob.get("/api/persons", params={"q": q}).json() == []
    assert bob.get("/api/facts/labels").json() == []
    assert bob.get("/api/me").status_code == 404
    for path in ("", "/facts", "/notes", "/relationships"):
        assert bob.get(f"/api/persons/{kari['id']}{path}").status_code == 404


def test_other_users_data_cannot_be_changed(two_users):
    bob, alice, kari, lars = two_users["bob"], two_users["alice"], two_users["kari"], two_users["lars"]
    fact, note, rel = two_users["fact"], two_users["note"], two_users["rel"]

    assert bob.patch(f"/api/persons/{kari['id']}", json={"first_name": "Hacked"}).status_code == 404
    assert bob.delete(f"/api/persons/{kari['id']}").status_code == 404
    assert bob.patch(f"/api/facts/{fact['id']}", json={"value": "Hacked"}).status_code == 404
    assert bob.delete(f"/api/facts/{fact['id']}").status_code == 404
    assert bob.patch(f"/api/notes/{note['id']}", json={"body": "Hacked"}).status_code == 404
    assert bob.delete(f"/api/notes/{note['id']}").status_code == 404
    assert bob.delete(f"/api/relationships/{rel['id']}").status_code == 404
    assert bob.post(f"/api/persons/{kari['id']}/facts", json={"label": "x", "value": "y"}).status_code == 404
    assert bob.post(f"/api/persons/{kari['id']}/notes", json={"body": "x"}).status_code == 404

    # Linking his own contact to Alice's is refused too.
    mine = bob.post("/api/persons", json={"first_name": "Bobs venn"}).json()
    res = bob.post("/api/relationships", json={"person_id": mine["id"], "other_id": kari["id"], "relation": "friend"})
    assert res.status_code == 404

    # Alice's data is untouched.
    assert alice.get(f"/api/persons/{kari['id']}").json()["first_name"] == "Kari"
    assert [f["value"] for f in alice.get(f"/api/persons/{kari['id']}/facts").json()] == ["Bamse"]
    assert len(alice.get(f"/api/persons/{kari['id']}/notes").json()) == 1
    assert [r["other"]["first_name"] for r in alice.get(f"/api/persons/{lars['id']}/relationships").json()] == ["Kari"]


def test_each_user_has_their_own_profile_and_data(two_users):
    alice, bob = two_users["alice"], two_users["bob"]
    assert bob.put("/api/me", json={"first_name": "Bob"}).status_code == 201
    assert alice.get("/api/me").json()["first_name"] == "Alice"
    assert bob.get("/api/me").json()["first_name"] == "Bob"
    # Bob's new contacts don't show up for Alice.
    bob.post("/api/persons", json={"first_name": "Bobs kollega"})
    assert {p["first_name"] for p in alice.get("/api/persons").json()} == {"Kari", "Lars"}
