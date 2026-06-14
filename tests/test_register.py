"""Tests for the registration flow (GET/POST /register)."""

from werkzeug.security import check_password_hash

import database.db as db


def _user_count():
    conn = db.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def test_get_register_renders(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"Create your account" in resp.data


def test_post_valid_creates_user_and_redirects(client):
    resp = client.post(
        "/register",
        data={"name": "Asha Rao", "email": "asha@example.com", "password": "secret123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")

    user = db.get_user_by_email("asha@example.com")
    assert user is not None
    assert user["name"] == "Asha Rao"
    assert user["password_hash"] != "secret123"
    assert check_password_hash(user["password_hash"], "secret123")


def test_post_duplicate_email_no_dup_and_shows_error(client):
    db.create_user("Existing", "dup@example.com", "x")
    assert _user_count() == 1

    resp = client.post(
        "/register",
        # Mixed case confirms lowercase normalization catches the duplicate.
        data={"name": "Other", "email": "DUP@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data
    assert _user_count() == 1


def test_post_blank_name_shows_error_no_row(client):
    resp = client.post(
        "/register",
        data={"name": "   ", "email": "x@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert b"required" in resp.data
    assert _user_count() == 0


def test_post_short_password_shows_error_no_row(client):
    resp = client.post(
        "/register",
        data={"name": "Short Pw", "email": "x@example.com", "password": "1234567"},
    )
    assert resp.status_code == 200
    assert b"8 characters" in resp.data
    assert _user_count() == 0


def test_post_invalid_email_shows_error_no_row(client):
    resp = client.post(
        "/register",
        data={"name": "Bad Email", "email": "not-an-email", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert b"valid email" in resp.data
    assert _user_count() == 0


def test_post_error_repopulates_name_and_email(client):
    resp = client.post(
        "/register",
        # Short password triggers an error so we can inspect the re-render.
        data={"name": "Keep Me", "email": "keep@example.com", "password": "short"},
    )
    assert resp.status_code == 200
    assert b"Keep Me" in resp.data
    assert b"keep@example.com" in resp.data
    assert b"short" not in resp.data


def test_email_stored_lowercase(client):
    client.post(
        "/register",
        data={"name": "Case Test", "email": "MixedCase@Example.COM", "password": "secret123"},
    )
    assert db.get_user_by_email("mixedcase@example.com") is not None
