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
