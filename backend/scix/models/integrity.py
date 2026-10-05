"""Integrity layer: AuditLog, Version, FigureAudit, Export.

Source: docs/06-integrity-authorship.md, S2 3.12, S2 3.13, S2 3.15.

IRREVERSIBLE (docs/08-roadmap.md 8.6): ``AuditLog.attribution`` is NOT NULL and
``actor_user_id`` is constrained against it. Retrofitting attribution means history that
was never attributed -- precisely the failure this product exists to prevent. S1 L354:
"Every change is labeled at the moment it happens -- not disclosed after the fact."
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scix.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_col, optional_enum_col
from scix.models.enums import (
    Attributed,
    AuditCheckCode,
    AuditSeverity,
    ExportFormat,
    TargetKind,
)


class AuditLog(Base):
    """Append-only event log. The backbone of the Research Integrity layer.

    There is deliberately NO updated_at: rows are never mutated. An UPDATE or DELETE on
    this table is a bug, and the absence of the columns is the first line of defence --
    there is nothing to update even by accident.

    The CHECK constraints below make attribution structural:

      * ``attribution`` is NOT NULL -- no event can exist without an author label
      * ``actor_user_id IS NULL  <=>  attribution = 'software'`` -- a machine action
        cannot be attributed to a person, and a person cannot be laundered into a
        machine action
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "(actor_user_id IS NULL) = (attribution = 'SOFTWARE')",
            name="actor_matches_attribution",
        ),
        Index("ix_audit_logs_project_created", "project_id", "created_at"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
        Index("ix_audit_logs_batch", "batch_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # The TWO values the spec allows, and no others (docs/01 R5).
    attribution: Mapped[Attributed] = enum_col(Attributed, "attributed")
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    # WHICH software component: grammar, consistency, plotly, matplotlib, llm...
    actor_component: Mapped[str | None] = mapped_column(String(64))
    # Reproducibility: the version that acted. S2 3.13 "Version: v1.4".
    tool_version: Mapped[str | None] = mapped_column(String(32))

    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[TargetKind] = enum_col(TargetKind, "target_kind")
    target_id: Mapped[str | None] = mapped_column(String(64))

    before_value: Mapped[dict | None] = mapped_column()
    after_value: Mapped[dict | None] = mapped_column()
    detail: Mapped[dict | None] = mapped_column()

    # Groups a document-wide run, e.g. a consistency rewrite that produced 400
    # individual changes. docs/02 2.7 requires ONE row per replacement, not a summary.
    batch_id: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Version(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Revision history for manuscript sections, graphs, figures and datasets.

    Carries ``author_type`` so a version history doubles as an authorship history --
    the S1 authorship matrix, applied to history rather than to a single state.
    """

    __tablename__ = "versions"
    __table_args__ = (
        CheckConstraint(
            "(author_user_id IS NULL) = (author_type = 'SOFTWARE')",
            name="version_author_matches_type",
    ),
        Index("ix_versions_scope", "scope", "scope_id"),
        Index("ix_versions_project_created", "project_id", "created_at"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scope: Mapped[TargetKind] = enum_col(TargetKind, "target_kind_scope")
    scope_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(nullable=False)

    author_type: Mapped[Attributed] = enum_col(Attributed, "attributed_version_author")
    author_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    parent_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("versions.id", ondelete="SET NULL")
    )
    message: Mapped[str | None] = mapped_column(Text)


class FigureAudit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One run of the S2 3.12 twelve-point figure audit.

    Persisted rather than computed on demand so the audit has a history: "this figure
    failed the unit check when it was submitted" is an answer the platform should be
    able to give.
    """

    __tablename__ = "figure_audits"
    __table_args__ = (
        Index("ix_figure_audits_figure_created", "graph_id", "created_at"),
    )

    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    checks: Mapped[list] = mapped_column(nullable=False)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    warn_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    blocking_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    acknowledged_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Export(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """S2 3.15 export engine. Every exported artefact is recorded, because
    "what was submitted, in what format, with which journal rules" is part of the
    traceability chain (docs/06 6.11)."""

    __tablename__ = "exports"
    __table_args__ = (
        Index("ix_exports_project_created", "project_id", "created_at"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_type: Mapped[TargetKind] = enum_col(TargetKind, "target_kind_export")
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    export_format: Mapped[ExportFormat] = enum_col(ExportFormat, "export_format")
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)

    journal_preset_id: Mapped[str | None] = mapped_column(
        ForeignKey("journal_presets.id", ondelete="SET NULL")
    )
    # Provenance snapshot embedded in the artefact, frozen at export time.
    provenance: Mapped[dict | None] = mapped_column()

    # Reproducibility: which renderer produced this, and at which version (ADR 0003).
    renderer: Mapped[str | None] = mapped_column(String(64))
    renderer_version: Mapped[str | None] = mapped_column(String(32))

    exported_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
