"""Shared test fixtures.

Every test runs against the real Postgres from docker-compose.yml -- not SQLite.
The constraints under test are native Postgres enums, JSONB and CHECK constraints,
none of which behave the same way in SQLite, so an SQLite test suite would pass while
proving nothing.
"""
from __future__ import annotations

import os
import uuid

import pytest

os.environ.setdefault(
    "SCIX_DATABASE_URL", "postgresql+psycopg://scix:scix@localhost:5433/scix_test"
)

from scix.core.config import get_settings  # noqa: E402
from scix.db.base import Base  # noqa: E402
from scix.db.session import get_engine, session_scope  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db():
    """A session that is rolled back, so tests are order-independent."""
    from scix.db.session import get_session_factory

    session = get_session_factory()()
    tx = session.begin()
    try:
        yield session
    finally:
        tx.rollback()
        session.close()


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture()
def uniq() -> str:
    return uuid.uuid4().hex[:10]


@pytest.fixture()
def user_factory():
    """Create committed users. Committed rather than rolled back because
    audit_logs uses ON DELETE RESTRICT and many tests need real FK targets."""

    def _make(role: str = "researcher"):
        from scix.models import User
        from scix.models.enums import UserRole

        with session_scope() as s:
            u = User(
                email=f"user-{uuid.uuid4().hex[:10]}@test.local",
                full_name="Test Researcher",
                hashed_password="not-a-real-hash",
                role=UserRole(role),
            )
            s.add(u)
            s.flush()
            return u.id

    return _make


@pytest.fixture()
def project_factory(user_factory):
    def _make(owner_id):
        from scix.models import Project

        with session_scope() as s:
            p = Project(owner_id=owner_id, name="Nanomaterial Study")
            s.add(p)
            s.flush()
            return p.id

    return _make
