"""Tests for the profile page (GET /profile) — now backed by real DB data (Step 5)."""

import database.db as db


def _login(client, user_id=1, name="Demo User"):
    """Seed a logged-in session for the given user id."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["name"] = name


def test_profile_redirects_when_logged_out(client):
    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_renders_when_logged_in(client, seeded_db):
    _login(client)
    resp = client.get("/profile")
    assert resp.status_code == 200


def test_profile_shows_user_card(client, seeded_db):
    _login(client)
    text = client.get("/profile").get_data(as_text=True)
    assert "Demo User" in text
    assert "demo@spendly.com" in text


def test_profile_shows_real_stats(client, seeded_db):
    _login(client)
    text = client.get("/profile").get_data(as_text=True)
    assert "₹274.84" in text                          # actual seed total
    assert 'class="profile-stat-value">8<' in text     # transaction count
    assert "Bills" in text                             # top category


def test_profile_transactions_newest_first(client, seeded_db):
    _login(client)
    text = client.get("/profile").get_data(as_text=True)
    # Day-22 expense must appear before the day-3 expense.
    assert text.index("Coffee and snack") < text.index("Lunch at cafe")


def test_profile_shows_category_breakdown(client, seeded_db):
    _login(client)
    text = client.get("/profile").get_data(as_text=True)
    for category in ("Bills", "Shopping", "Transport", "Health", "Other", "Food", "Entertainment"):
        assert category in text


def test_profile_navbar_logged_in(client, seeded_db):
    _login(client)
    text = client.get("/profile").get_data(as_text=True)
    assert "Sign out" in text


def test_profile_empty_state_for_new_user(client):
    # A brand-new user with no expenses (id is independent of any seeded demo user).
    user_id = db.create_user("New User", "new@example.com", "x")
    _login(client, user_id=user_id, name="New User")
    text = client.get("/profile").get_data(as_text=True)
    assert "₹0.00" in text
    assert "No expenses yet" in text
