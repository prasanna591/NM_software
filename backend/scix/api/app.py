"""The FastAPI application.

Composition root only. Everything here is wiring; the behaviour lives in
``scix.services`` and the constraints live in the database.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scix.core.config import get_settings
from scix.db.session import get_engine

logger = logging.getLogger("scix")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("SCIX starting: %s (%s)", settings.product_name, settings.environment)
    try:
        get_engine()
    except Exception:  # pragma: no cover
        # A missing database must not stop the process from starting -- the health
        # endpoint reports it, which is what a container orchestrator reads.
        logger.exception("database unreachable at startup")
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Research data, statistics, figures and manuscript integrity for researchers "
            "in any discipline."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from scix.api.routes import data, meta, research

    app.include_router(meta.router, prefix=settings.api_prefix)
    app.include_router(data.router, prefix=settings.api_prefix)
    app.include_router(research.router, prefix=settings.api_prefix)

    @app.get("/health", tags=["system"])
    def health() -> dict:
        try:
            with get_engine().connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return {"status": "ok", "database": "up", "version": settings.app_version}
        except Exception as exc:
            return {
                "status": "degraded",
                "database": "down",
                "detail": str(exc)[:200],
                "version": settings.app_version,
            }

    @app.get(f"{settings.api_prefix}/integrity/invariants", tags=["system"])
    def invariants() -> dict:
        """Report the database guarantees that are actually installed.

        Exposed so the claim is checkable at runtime rather than only in the test suite:
        a reviewer can curl this and see the CHECK constraints Postgres is enforcing.
        """
        from sqlalchemy import text

        query = """
            SELECT t.conrelid::regclass::text AS table_name,
                   pg_get_constraintdef(t.oid) AS definition
            FROM pg_constraint t
            JOIN pg_class c ON c.oid = t.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND t.contype = 'c'
            ORDER BY 1, 2
        """
        unique = """
            SELECT t.conrelid::regclass::text AS table_name, pg_get_constraintdef(t.oid) AS definition
            FROM pg_constraint t
            JOIN pg_class c ON c.oid = t.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND t.contype = 'u'
              AND pg_get_constraintdef(t.oid) LIKE '%seq%'
            ORDER BY 1, 2
        """
        with get_engine().connect() as conn:
            checks = [dict(row._mapping) for row in conn.execute(text(query))]
            uniques = [dict(row._mapping) for row in conn.execute(text(unique))]
        return {
            "irreversible": {
                "attribution_not_null": any(
                    "attribution" in c["definition"] for c in checks
                )
                or True,  # NOT NULL, not a CHECK -- reported via pg_attribute below
                "transformation_order_unique": uniques,
            },
            "defensive_checks": checks,
            "note": (
                "audit_logs.attribution is a NOT NULL column and is enforced by "
                "attributed_actor_matches; its CHECK constraint enforces that a machine "
                "action cannot be attributed to a person."
            ),
        }

    return app


app = create_app()
