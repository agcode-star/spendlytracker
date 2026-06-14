"""Shared pytest fixtures for the database layer.

Each fixture redirects database.db.DB_PATH to a throwaway file under pytest's
tmp_path, so tests never touch the real spendly.db.
"""

import pytest

import database.db as db


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """An initialized (schema-only) database pointed at a temp file."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_spendly.db"))
    db.init_db()
    yield db


@pytest.fixture
def seeded_db(test_db):
    """An initialized database that has also been seeded with demo data."""
    test_db.seed_db()
    yield test_db
