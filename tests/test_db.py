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
