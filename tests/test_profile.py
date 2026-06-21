"""Tests for the profile page (GET /profile) — UI-only, hardcoded data (Step 4)."""


def _login(client):
    """Seed a logged-in session without needing a real DB user."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["name"] = "Demo User"


def test_profile_redirects_when_logged_out(client):
    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_renders_when_logged_in(client):
    _login(client)
    resp = client.get("/profile")
    assert resp.status_code == 200


def test_profile_shows_user_card(client):
    _login(client)
    resp = client.get("/profile")
    assert b"Demo User" in resp.data
    assert b"demo@spendly.com" in resp.data


def test_profile_shows_stats(client):
    _login(client)
    resp = client.get("/profile")
    assert b"Total spent" in resp.data
    assert b"Transactions" in resp.data
    assert b"Top category" in resp.data


def test_profile_shows_transactions(client):
    _login(client)
    resp = client.get("/profile")
    # At least three transaction descriptions appear in the table.
    assert b"Lunch at cafe" in resp.data
    assert b"Metro pass" in resp.data
    assert b"Electricity bill" in resp.data
    assert resp.data.count(b"badge badge-") >= 3


def test_profile_shows_category_breakdown(client):
    _login(client)
    resp = client.get("/profile")
    assert b"Category breakdown" in resp.data
    assert b"Food" in resp.data
    assert b"Bills" in resp.data
    assert b"Transport" in resp.data


def test_profile_navbar_logged_in(client):
    _login(client)
    resp = client.get("/profile")
    assert b"Sign out" in resp.data
