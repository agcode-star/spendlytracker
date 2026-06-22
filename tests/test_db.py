"""Tests for the SQLite data layer (database/db.py)."""

import sqlite3
from datetime import datetime

import pytest

from werkzeug.security import check_password_hash

import database.db as db


def _table_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row["name"] for row in rows}


def _columns(conn, table):
    # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"]: row for row in rows}


def test_tables_exist(test_db):
    conn = test_db.get_db()
    try:
        names = _table_names(conn)
        assert "users" in names
        assert "expenses" in names
    finally:
        conn.close()


def test_users_columns(test_db):
    conn = test_db.get_db()
    try:
        cols = _columns(conn, "users")
        assert set(cols) == {"id", "name", "email", "password_hash", "created_at"}
        assert cols["name"]["notnull"] == 1
        assert cols["email"]["notnull"] == 1
        assert cols["password_hash"]["notnull"] == 1
    finally:
        conn.close()


def test_expenses_columns(test_db):
    conn = test_db.get_db()
    try:
        cols = _columns(conn, "expenses")
        assert set(cols) == {
            "id", "user_id", "amount", "category", "date", "description", "created_at",
        }
        assert cols["user_id"]["notnull"] == 1
        assert cols["amount"]["notnull"] == 1
        # description is nullable
        assert cols["description"]["notnull"] == 0
    finally:
        conn.close()


def test_get_db_row_factory(test_db):
    conn = test_db.get_db()
    try:
        assert conn.row_factory is sqlite3.Row
        row = conn.execute("SELECT 1 AS one").fetchone()
        assert row["one"] == 1  # key-based access works
    finally:
        conn.close()


def test_get_db_foreign_keys_on(test_db):
    conn = test_db.get_db()
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_init_db_idempotent(test_db):
    # init_db already ran via the fixture; running again must not error.
    test_db.init_db()
    conn = test_db.get_db()
    try:
        assert {"users", "expenses"} <= _table_names(conn)
    finally:
        conn.close()


def test_seed_inserts_demo_user_and_8_expenses(seeded_db):
    conn = seeded_db.get_db()
    try:
        users = conn.execute("SELECT * FROM users").fetchall()
        assert len(users) == 1
        assert users[0]["email"] == "demo@spendly.com"
        assert users[0]["name"] == "Demo User"
        demo_id = users[0]["id"]

        expenses = conn.execute("SELECT * FROM expenses").fetchall()
        assert len(expenses) == 8
        assert all(e["user_id"] == demo_id for e in expenses)
    finally:
        conn.close()


def test_seed_password_hashed(seeded_db):
    conn = seeded_db.get_db()
    try:
        stored = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()["password_hash"]
        assert stored != "demo123"
        assert check_password_hash(stored, "demo123")
    finally:
        conn.close()


def test_seed_idempotent_no_duplicates(seeded_db):
    seeded_db.seed_db()  # second call
    conn = seeded_db.get_db()
    try:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 8
    finally:
        conn.close()


def test_all_categories_represented(seeded_db):
    conn = seeded_db.get_db()
    try:
        rows = conn.execute("SELECT DISTINCT category FROM expenses").fetchall()
        categories = {r["category"] for r in rows}
        assert set(db.CATEGORIES) <= categories
    finally:
        conn.close()


def test_seed_dates_current_month(seeded_db):
    prefix = datetime.now().strftime("%Y-%m")
    conn = seeded_db.get_db()
    try:
        dates = [r["date"] for r in conn.execute("SELECT date FROM expenses").fetchall()]
        for d in dates:
            assert d.startswith(prefix)
            # YYYY-MM-DD format
            datetime.strptime(d, "%Y-%m-%d")
    finally:
        conn.close()


def test_unique_email_constraint(seeded_db):
    conn = seeded_db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Dupe", "demo@spendly.com", "x"),
            )
            conn.commit()
    finally:
        conn.close()


def test_fk_enforced_bad_user_id(seeded_db):
    conn = seeded_db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (99999, 10.0, "Food", "2026-06-01", "bad fk"),
            )
            conn.commit()
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# Step 5 profile-data helpers                                         #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(seeded_db):
    user = seeded_db.get_user_by_id(1)
    assert user is not None
    assert user["email"] == "demo@spendly.com"


def test_get_user_by_id_missing(test_db):
    assert test_db.get_user_by_id(999) is None


def test_get_recent_expenses_returns_all_newest_first(seeded_db):
    rows = seeded_db.get_recent_expenses(1)
    assert len(rows) == 8
    # Newest date first (day 22), oldest last (day 3).
    assert rows[0]["description"] == "Coffee and snack"
    assert rows[-1]["description"] == "Lunch at cafe"
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates, reverse=True)


def test_get_recent_expenses_respects_limit(seeded_db):
    rows = seeded_db.get_recent_expenses(1, limit=3)
    assert len(rows) == 3
    assert rows[0]["description"] == "Coffee and snack"
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates, reverse=True)


def test_get_recent_expenses_empty_for_user_with_none(test_db):
    user_id = test_db.create_user("No Spend", "nospend@spendly.com", "x")
    assert test_db.get_recent_expenses(user_id) == []
    assert test_db.get_recent_expenses(999) == []


def test_get_recent_expenses_is_user_scoped(seeded_db):
    other_id = seeded_db.create_user("Other", "other@spendly.com", "x")
    conn = seeded_db.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (other_id, 5.0, "Food", "2026-06-30", "other user expense"),
        )
        conn.commit()
    finally:
        conn.close()

    demo_rows = seeded_db.get_recent_expenses(1)
    assert len(demo_rows) == 8
    assert all(r["user_id"] == 1 for r in demo_rows)

    other_rows = seeded_db.get_recent_expenses(other_id)
    assert len(other_rows) == 1
    assert all(r["user_id"] == other_id for r in other_rows)


def test_get_expense_summary_seeded_user(seeded_db):
    summary = seeded_db.get_expense_summary(1)
    assert summary["total"] == pytest.approx(274.84)
    assert summary["count"] == 8
    assert summary["top_category"] == "Bills"


def test_get_expense_summary_no_expenses(test_db):
    user_id = test_db.create_user("Empty", "empty@spendly.com", "x")
    summary = test_db.get_expense_summary(user_id)
    assert summary["total"] == pytest.approx(0)
    assert summary["count"] == 0
    assert summary["top_category"] is None

    missing = test_db.get_expense_summary(999)
    assert missing == {"total": 0, "count": 0, "top_category": None}


def test_get_expense_summary_per_user_isolation(seeded_db):
    other_id = seeded_db.create_user("Other", "other@spendly.com", "x")
    conn = seeded_db.get_db()
    try:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (other_id, 100.00, "Transport", "2026-06-01", "Flight"),
                (other_id, 5.00, "Food", "2026-06-02", "Snack"),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    other = seeded_db.get_expense_summary(other_id)
    assert other["total"] == pytest.approx(105.00)
    assert other["count"] == 2
    assert other["top_category"] == "Transport"

    seeded = seeded_db.get_expense_summary(1)
    assert seeded["total"] == pytest.approx(274.84)
    assert seeded["count"] == 8
    assert seeded["top_category"] == "Bills"


def test_category_breakdown_seeded_user(seeded_db):
    breakdown = seeded_db.get_category_breakdown(1)
    assert len(breakdown) == 7
    assert breakdown[0]["category"] == "Bills"
    assert breakdown[0]["total"] == pytest.approx(85.20)
    food = next(b for b in breakdown if b["category"] == "Food")
    assert food["total"] == pytest.approx(20.90)
    totals = [b["total"] for b in breakdown]
    assert totals == sorted(totals, reverse=True)


def test_category_breakdown_expected_order(seeded_db):
    breakdown = seeded_db.get_category_breakdown(1)
    categories = [b["category"] for b in breakdown]
    assert categories == [
        "Bills", "Shopping", "Transport", "Health", "Other", "Food", "Entertainment",
    ]


def test_category_breakdown_no_expenses(test_db):
    user_id = test_db.create_user("Empty", "empty@spendly.com", "x")
    assert test_db.get_category_breakdown(user_id) == []
    assert test_db.get_category_breakdown(999) == []


def test_category_breakdown_per_user_isolation(seeded_db):
    other_id = seeded_db.create_user("Other", "other@spendly.com", "x")
    conn = seeded_db.get_db()
    try:
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (other_id, 5.00, "Food", "2026-06-01", "snack"),
                (other_id, 100.00, "Transport", "2026-06-02", "flight"),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    breakdown = seeded_db.get_category_breakdown(other_id)
    assert [b["category"] for b in breakdown] == ["Transport", "Food"]
    assert breakdown[0]["total"] == pytest.approx(100.00)
    assert breakdown[1]["total"] == pytest.approx(5.00)
