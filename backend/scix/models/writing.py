"""Writing layer: WritingSuggestion, SuggestionDecision, SuggestionRejection.

Defined in ADR 0002 (Q10) -- absent from S2's schema entirely, despite the Writing
module being half the product.

R6: no suggestion may be applied without a recorded human decision. ``decided_by_id`` is
NOT NULL and there is no application code path that mutates a section without one.
"""
from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scix.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_col, optional_enum_col
from scix.models.enums import (
    Attributed,
    SuggestionDecisionKind,
    SuggestionStatus,
    WritingTool,
)


class WritingSuggestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One machine suggestion. A record of machine OUTPUT -- never of applied change.

    ``offset_start``/``offset_end`` locate the suggestion in the revision it was computed
    against. Because a consistency run rewrites the document, earlier pending
    suggestions whose ranges no longer match are marked SUPERSEDED rather than left to
    fail on apply (ADR 0002).
    """

    __tablename__ = "writing_suggestions"
    __table_args__ = (
        Index("ix_writing_suggestions_section_status", "section_id", "status"),
        Index("ix_writing_suggestions_revision", "revision_id"),
        Index("ix_writing_suggestions_batch", "batch_id"),
        CheckConstraint(
            "offset_start >= 0 AND offset_end >= offset_start",
            name="offset_range_valid",
        ),
    )

    section_id: Mapped[str] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True, nullable=False
    )
    revision_id: Mapped[str] = mapped_column(
        ForeignKey("manuscript_revisions.id", ondelete="CASCADE"), nullable=False
    )
    tool: Mapped[WritingTool] = enum_col(WritingTool, "writing_tool")
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info", server_default="info")

    offset_start: Mapped[int] = mapped_column(Integer, nullable=False)
    offset_end: Mapped[int] = mapped_column(Integer, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    deletions: Mapped[list | None] = mapped_column()
    insertions: Mapped[list | None] = mapped_column()

    # Groups a document-wide run, e.g. a consistency rewrite.
    batch_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[SuggestionStatus] = enum_col(
        SuggestionStatus, "suggestion_status", default=SuggestionStatus.PENDING,
        server_default="PENDING",
    )
    # Which software component produced it. Always software: a machine cannot suggest.
    attribution: Mapped[Attributed] = enum_col(
        Attributed, "attributed_suggestion", server_default="SOFTWARE"
    )
    tool_version: Mapped[str | None] = mapped_column(String(32))

    decisions: Mapped[list["SuggestionDecision"]] = relationship(
        back_populates="suggestion", cascade="all, delete-orphan"
    )


class SuggestionDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The human response. S1 L253-257: Accept, Edit, Reject.

    ``decided_by_id`` is NOT NULL (R6). ``final_text`` is set when the researcher EDITS
    a suggestion -- the result is still attributed SOFTWARE (the suggestion came from
    software) but with ``decision = 'edit'`` and the researcher's text preserved.
    A direct paragraph edit is a separate HUMAN action on the section itself.
    """

    __tablename__ = "suggestion_decisions"
    __table_args__ = (
        CheckConstraint(
            "(decision = 'EDIT') = (final_text IS NOT NULL)",
            name="edit_requires_final_text",
        ),
        Index("ix_suggestion_decisions_suggestion", "suggestion_id"),
    )

    suggestion_id: Mapped[str] = mapped_column(
        ForeignKey("writing_suggestions.id", ondelete="CASCADE"), nullable=False
    )
    suggestion: Mapped[WritingSuggestion] = relationship(back_populates="decisions")
    decision: Mapped[SuggestionDecisionKind] = enum_col(
        SuggestionDecisionKind, "suggestion_decision_kind"
    )
    final_text: Mapped[str | None] = mapped_column(Text)
    decided_by_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # What was actually written to the section, for the version diff.
    applied_result: Mapped[dict | None] = mapped_column()


class SuggestionRejection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A persistent dismissal. Q17.

    Repeatedly rejecting the same false positive is a real failure mode for a tool meant
    to be run often. A rejection is keyed on (user, rule, normalised context) and
    suppresses the suggestion until the underlying text changes -- so correcting the
    sentence brings the suggestion back, which is the correct behaviour.
    """

    __tablename__ = "suggestion_rejections"
    __table_args__ = (
        Index("ix_suggestion_rejections_lookup", "user_id", "rule_id", "context_hash"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[str | None] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE")
    )
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    reject_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
