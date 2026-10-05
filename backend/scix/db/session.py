"""Database engine and session.

The engine is configured for the write-once, append-heavy pattern of the integrity
layer: audit_logs is insert-only and never updated, so committing the session is cheap.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from scix.core.config import get_settings
from scix.db.base import Base
import scix.models  # noqa: F401  -- registers every table on Base.metadata

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.sql_echo,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope. Used by services, which must commit atomically."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def create_all() -> None:
    """Create the full schema.

    Used for tests and local bootstrap. Production migrations go through Alembic --
    but both paths build from the SAME ``Base.metadata``, so the constraints cannot
    diverge. See alembic/env.py.
    """
    Base.metadata.create_all(bind=get_engine())


def drop_all() -> None:
    Base.metadata.drop_all(bind=get_engine())
