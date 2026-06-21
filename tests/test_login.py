"""Tests for the login/logout flow (GET/POST /login, GET /logout)."""

from werkzeug.security import generate_password_hash

import database.db as db


def _make_user(name="Test User", email="test@example.com", password="secret123"):
    """Create a user in the temp DB and return its id."""
    return db.create_user(name, email, generate_password_hash(password))


def test_get_login_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Welcome back" in resp.data


def test_post_valid_logs_in_and_redirects(client):
    user_id = _make_user()
    resp = client.post(
        "/login",
        data={"email": "test@example.com", "password": "secret123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    with client.session_transaction() as sess:
        assert sess["user_id"] == user_id
        assert sess["name"] == "Test User"


def test_post_wrong_password_generic_error_no_session(client):
    _make_user()
    resp = client.post(
        "/login",
        data={"email": "test@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 200
    assert b"Invalid email or password." in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_post_unknown_email_generic_error_no_session(client):
    resp = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    # Identical message to the wrong-password case → no user enumeration.
    assert b"Invalid email or password." in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_post_error_repopulates_email_not_password(client):
    _make_user()
    resp = client.post(
        "/login",
        data={"email": "test@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 200
    assert b"test@example.com" in resp.data
    assert b"wrongpass" not in resp.data


def test_email_normalized_on_login(client):
    _make_user(email="test@example.com")
    resp = client.post(
        "/login",
        data={"email": "  TEST@Example.COM  ", "password": "secret123"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_logout_clears_session_and_redirects(client):
    _make_user()
    client.post(
        "/login",
        data={"email": "test@example.com", "password": "secret123"},
    )
    resp = client.get("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_logged_in_user_redirected_from_login(client):
    # A signed-in user visiting /login is bounced to their profile page.
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["name"] = "Test User"
    resp = client.get("/login", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_navbar_reflects_session(client):
    # Logged out: landing shows the public links, not "Sign out".
    resp = client.get("/")
    assert b"Sign in" in resp.data
    assert b"Sign out" not in resp.data

    # Logged in: seed the session directly, then the navbar switches.
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["name"] = "Test User"
    resp = client.get("/")
    assert b"Sign out" in resp.data
    assert b"Test User" in resp.data
