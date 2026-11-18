from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from tests.conftest import PASSWORD

EMAIL = "bob@example.com"


def start_login(client, email=EMAIL, password=PASSWORD, **extra):
    return client.post("/api/auth/login", json={"email": email, "password": password, **extra})


def test_login_with_emailed_code(anon_client, create_user, mailer):
    create_user(EMAIL)
    assert anon_client.get("/api/auth/me").status_code == 401

    res = start_login(anon_client, email="  Bob@Example.com ")  # email is case/whitespace-insensitive
    assert res.status_code == 200
    challenge_id = res.json()["challenge_id"]
    to, subject, body = mailer.sent[-1]
    assert to == EMAIL and "Mimre" in subject
    code = mailer.last_code(EMAIL)
    assert code in body

    res = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": code})
    assert res.status_code == 200
    assert res.json()["email"] == EMAIL

    cookie = res.headers["set-cookie"].lower()
    assert "mimre_session=" in cookie and "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert anon_client.get("/api/auth/me").json()["email"] == EMAIL

    # A code can only be used once.
    again = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": code})
    assert again.status_code == 401 and again.json()["detail"] == "challenge_expired"


def test_wrong_password_and_unknown_email_look_the_same(anon_client, create_user, mailer):
    create_user(EMAIL)
    wrong = start_login(anon_client, password="wrong password!")
    unknown = start_login(anon_client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "invalid_credentials"}
    assert mailer.sent == []


def test_account_locks_after_repeated_wrong_passwords(anon_client, create_user):
    create_user(EMAIL)
    for _ in range(5):
        assert start_login(anon_client, password="wrong password!").status_code == 401
    res = start_login(anon_client)  # even the right password is refused while locked
    assert res.status_code == 429 and res.json()["detail"] == "locked"


def test_wrong_code_and_attempt_limit(anon_client, create_user, mailer):
    create_user(EMAIL)
    challenge_id = start_login(anon_client).json()["challenge_id"]
    right = mailer.last_code(EMAIL)
    wrong = "000000" if right != "000000" else "111111"

    for _ in range(4):
        res = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": wrong})
        assert res.status_code == 401 and res.json()["detail"] == "invalid_code"
    res = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": wrong})
    assert res.json()["detail"] == "challenge_expired"
    # After too many attempts even the right code no longer works.
    res = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": right})
    assert res.status_code == 401 and res.json()["detail"] == "challenge_expired"


def test_expired_code(anon_client, create_user, mailer, admin_engine):
    create_user(EMAIL)
    challenge_id = start_login(anon_client).json()["challenge_id"]
    with admin_engine.begin() as conn:
        conn.execute(text("UPDATE login_challenges SET expires_at = now() - interval '1 second'"))
    res = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": mailer.last_code(EMAIL)})
    assert res.status_code == 401 and res.json()["detail"] == "challenge_expired"


def test_resend_code(anon_client, create_user, mailer, admin_engine):
    create_user(EMAIL)
    challenge_id = start_login(anon_client).json()["challenge_id"]
    first = mailer.last_code(EMAIL)

    res = anon_client.post("/api/auth/resend", json={"challenge_id": challenge_id})
    assert res.status_code == 429 and res.json()["detail"] == "resend_too_soon"

    def allow_resend():
        with admin_engine.begin() as conn:
            conn.execute(text("UPDATE login_challenges SET last_sent_at = now() - interval '1 minute'"))

    allow_resend()
    assert anon_client.post("/api/auth/resend", json={"challenge_id": challenge_id, "language": "en"}).status_code == 204
    assert "login code" in mailer.sent[-1][1]  # English email
    second = mailer.last_code(EMAIL)
    if first != second:  # the old code stops working
        res = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": first})
        assert res.json()["detail"] == "invalid_code"

    allow_resend()
    assert anon_client.post("/api/auth/resend", json={"challenge_id": challenge_id}).status_code == 204
    allow_resend()
    res = anon_client.post("/api/auth/resend", json={"challenge_id": challenge_id})
    assert res.status_code == 429 and res.json()["detail"] == "too_many_codes"

    res = anon_client.post("/api/auth/verify", json={"challenge_id": challenge_id, "code": mailer.last_code(EMAIL)})
    assert res.status_code == 200


def test_logout_ends_session(client):
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/persons").status_code == 401


def test_expired_session_is_rejected(client, admin_engine):
    with admin_engine.begin() as conn:
        conn.execute(text("UPDATE auth_sessions SET expires_at = now() - interval '1 second'"))
    assert client.get("/api/persons").status_code == 401


def test_session_is_extended_while_in_use(client, admin_engine):
    old_expiry = datetime.now(UTC) + timedelta(days=2)
    with admin_engine.begin() as conn:
        conn.execute(
            text("UPDATE auth_sessions SET expires_at = :e, last_seen_at = now() - interval '2 days'"), {"e": old_expiry}
        )
    res = client.get("/api/persons")
    assert res.status_code == 200
    assert "mimre_session=" in res.headers.get("set-cookie", "")  # cookie refreshed too
    with admin_engine.begin() as conn:
        assert conn.scalar(text("SELECT expires_at FROM auth_sessions")) > old_expiry + timedelta(days=20)
