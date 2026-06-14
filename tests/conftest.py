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


@pytest.fixture
def client(test_db):
    """A Flask test client backed by the schema-only temp database.

    app is imported here (after test_db monkeypatches DB_PATH) so importing it
    never creates or seeds the real spendly.db. get_db() reads DB_PATH at call
    time, so the app's runtime queries hit the temp database too.
    """
    from app import app as flask_app

    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as client:
        yield client
