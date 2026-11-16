from datetime import timedelta

import pytest
from sqlalchemy import select

from api.auth import COOKIE_NAME, hash_password, utcnow, verify_password
from db.models import AdminSession, User


@pytest.fixture
def admin(session_factory):
    with session_factory() as db:
        db.add(User(username="moderator", password_hash=hash_password("test-password-123")))
        db.commit()


def login(client):
    response = client.post("/api/admin/login", json={"username": "moderator", "password": "test-password-123"})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_passwords_are_salted_and_verified():
    first = hash_password("password-one")
    assert first != hash_password("password-one")
    assert verify_password("password-one", first)
    assert not verify_password("wrong", first)
    assert not verify_password("x", "invalid")


def test_private_endpoints_need_login(client):
    assert client.get("/api/admin/me").status_code == 401
    assert client.get("/api/admin/events").status_code == 401
    assert client.put("/api/admin/events/1", json={}).status_code == 401


def test_login_cookie_session_and_logout(client, admin, session_factory):
    headers = login(client)
    assert client.cookies.get(COOKIE_NAME)
    assert client.get("/api/admin/me").json()["username"] == "moderator"
    with session_factory() as db:
        stored = db.scalar(select(AdminSession))
        assert stored.token_hash != client.cookies.get(COOKIE_NAME)
    assert client.post("/api/admin/logout").status_code == 403
    assert client.post("/api/admin/logout", headers=headers).status_code == 204
    assert client.get("/api/admin/me").status_code == 401


def test_login_cookie_is_http_only_and_secure_on_vercel(client, admin, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    response = client.post("/api/admin/login", json={"username": "moderator", "password": "test-password-123"})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert "path=/api/admin" in cookie


def test_login_and_mutations_reject_other_origins(client, admin):
    assert (
        client.post(
            "/api/admin/login",
            json={"username": "moderator", "password": "test-password-123"},
            headers={"Origin": "https://attacker.test"},
        ).status_code
        == 403
    )
    headers = login(client)
    assert client.post("/api/admin/logout", headers={**headers, "Origin": "https://attacker.test"}).status_code == 403


def test_expired_session_is_rejected(client, admin, session_factory):
    login(client)
    with session_factory() as db:
        db.scalar(select(AdminSession)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/admin/me").status_code == 401


def test_repeated_wrong_password_is_rate_limited(client, admin):
    for _ in range(5):
        assert client.post("/api/admin/login", json={"username": "moderator", "password": "wrong"}).status_code == 401
    assert client.post("/api/admin/login", json={"username": "moderator", "password": "wrong"}).status_code == 429


def test_pending_submission_can_be_corrected_published_and_rejected(client, admin, today):
    created = client.post(
        "/api/submissions",
        json={
            "title": "Научная встреча",
            "organizer": "ТПУ",
            "category": "science",
            "event_date": today.isoformat(),
            "contact": "private@example.com",
        },
    ).json()
    event_id = created["id"]
    assert client.get(f"/api/events/{event_id}").status_code == 404
    headers = login(client)
    queue = client.get("/api/admin/events").json()
    assert queue["items"][0]["contact"] == "private@example.com"
    data = {
        "title": "Исправленное название",
        "organizer": "ТПУ",
        "category": "science",
        "event_date": today.isoformat(),
        "location": "Онлайн",
        "status": "published",
    }
    assert client.put(f"/api/admin/events/{event_id}", json=data).status_code == 403
    published = client.put(f"/api/admin/events/{event_id}", json=data, headers=headers)
    assert published.status_code == 200
    public = client.get(f"/api/events/{event_id}").json()
    assert public["title"] == data["title"] and "contact" not in public
    assert (
        client.put(f"/api/admin/events/{event_id}", json={**data, "status": "rejected"}, headers=headers).status_code
        == 200
    )
    assert client.get(f"/api/events/{event_id}").status_code == 404


def test_cannot_publish_incomplete_collector_event(client, admin, add_event):
    event_id = add_event(status="pending", event_date=None)
    headers = login(client)
    data = {"title": "Событие", "organizer": "Клуб ТПУ", "status": "published", "event_date": "", "category": ""}
    response = client.put(f"/api/admin/events/{event_id}", json=data, headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "event_date"
    assert (
        client.put(f"/api/admin/events/{event_id}", json={**data, "status": "rejected"}, headers=headers).status_code
        == 200
    )


def test_database_configuration_rejects_sqlite_in_vercel(monkeypatch):
    from db.database import database_url

    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///calendar.db")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        database_url()


def test_create_admin_and_reset_password_revoke_sessions(session_factory, monkeypatch):
    import sys

    from db import create_admin

    monkeypatch.setattr(create_admin, "engine", session_factory.kw["bind"])
    monkeypatch.setattr(sys, "argv", ["create_admin", "newadmin"])
    monkeypatch.setattr(create_admin.getpass, "getpass", lambda prompt: "first-password-123")
    create_admin.main()
    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "newadmin"))
        assert verify_password("first-password-123", user.password_hash)
        from api.auth import new_session

        _, session = new_session(user.id)
        db.add(session)
        db.commit()
    monkeypatch.setattr(sys, "argv", ["create_admin", "newadmin", "--reset-password"])
    monkeypatch.setattr(create_admin.getpass, "getpass", lambda prompt: "changed-password-123")
    create_admin.main()
    with session_factory() as db:
        user = db.scalar(select(User).where(User.username == "newadmin"))
        assert verify_password("changed-password-123", user.password_hash)
        assert db.scalar(select(AdminSession)) is None


def test_cli_reports_failed_collection(monkeypatch):
    import sys

    from collector import run

    monkeypatch.setattr(sys, "argv", ["collector.run"])
    monkeypatch.setattr(run, "run", lambda limit: {"communities": 15, "failed_communities": 1, "errors": 0})
    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 1
