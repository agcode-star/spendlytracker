"""SQLite data layer for Spendly.

All database access lives here — routes never touch SQLite directly.
"""

import os
import sqlite3
from datetime import datetime

from werkzeug.security import generate_password_hash

# Resolve the DB path relative to this file so it is independent of the
# current working directory. database/db.py -> database/ -> project root.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "spendly.db")

# Fixed category list shared across the app.
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    """Return a SQLite connection with dict-like rows and FK enforcement on.

    SQLite disables foreign keys by default, so the PRAGMA must run on every
    connection. Reads DB_PATH at call time so tests can monkeypatch it.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they do not already exist.

    Idempotent — safe to call on every startup.
    """
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert a demo user and 8 sample expenses for development.

    Returns early if any users already exist, so repeated runs never
    duplicate the seed data.
    """
    conn = get_db()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if existing > 0:
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        now = datetime.now()
        year, month = now.year, now.month

        # (amount, category, day, description) — covers all 7 categories, with
        # one extra Food entry to reach 8. Days valid in any month.
        samples = [
            (12.50, "Food", 3, "Lunch at cafe"),
            (40.00, "Transport", 5, "Monthly metro pass"),
            (85.20, "Bills", 7, "Electricity bill"),
            (30.00, "Health", 10, "Pharmacy"),
            (15.99, "Entertainment", 12, "Movie ticket"),
            (60.75, "Shopping", 15, "New shoes"),
            (22.00, "Other", 18, "Gift"),
            (8.40, "Food", 22, "Coffee and snack"),
        ]
        rows = [
            (user_id, amount, category, f"{year:04d}-{month:02d}-{day:02d}", description)
            for amount, category, day, description in samples
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the user row for an email, or None if no such user exists.

    Read-only — callers should pass an already-normalised (lowercased) email so
    lookups stay consistent with how rows are stored.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password_hash):
    """Insert a new user and return the new row id.

    The password must already be hashed by the caller (mirrors seed_db). This
    helper is a pure insert and does no hashing or validation itself.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return the user row for an id, or None if no such user exists."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def get_recent_expenses(user_id, limit=10):
    """Return a user's most recent expenses, newest first.

    Read-only. Orders by date descending, then id descending so same-day rows
    are tie-broken by insertion order. Returns at most `limit` rows and an empty
    list when the user has no expenses.
    """
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? "
            "ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()


def get_expense_summary(user_id):
    """Return summary stats for a user's expenses as a dict.

    Read-only. Aggregates the user's expenses into:
        total        — sum of all amounts (0 when the user has none)
        count        — number of expense rows
        top_category — category with the largest summed amount, or None

    SUM() returns NULL for an empty set, so COALESCE guards total back to 0.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()

        return {
            "total": row["total"],
            "count": row["count"],
            "top_category": top["category"] if top is not None else None,
        }
    finally:
        conn.close()


def get_category_breakdown(user_id):
    """Return per-category expense totals for a user, highest total first.

    Yields one dict per category the user actually has expenses in:
    ``[{"category": <str>, "total": <float>}, ...]``. Returns an empty list
    when the user has no expenses. The view layer handles percentages and
    currency formatting — this is the raw summed total.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC",
            (user_id,),
        ).fetchall()
        return [{"category": row["category"], "total": row["total"]} for row in rows]
    finally:
        conn.close()
