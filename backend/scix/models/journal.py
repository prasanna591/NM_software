"""Journal presets -- S2 3.10.

Source: "The system shows the source and date of each journal requirement rather than
silently assuming outdated rules." (S2 L719)

This is a TRUST feature. ``rule_source`` and ``rule_verified_at`` are NOT NULL so that
a preset cannot exist without a provenance for its requirements, and so the UI can warn
when a rule is stale rather than quietly enforcing an out-of-date specification.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from scix.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JournalPreset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journal_presets"

    journal_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255))
    issn: Mapped[str | None] = mapped_column(String(32))

    # --- figure requirements ---
    width_mm: Mapped[float | None] = mapped_column()
    height_mm: Mapped[float | None] = mapped_column()
    resolution_dpi: Mapped[int | None] = mapped_column(Integer)
    file_format: Mapped[str | None] = mapped_column(String(32))
    font_family: Mapped[str | None] = mapped_column(String(128))
    min_font_pt: Mapped[float | None] = mapped_column()
    max_panels: Mapped[int | None] = mapped_column(Integer)
    color_requirements: Mapped[str | None] = mapped_column(Text)

    # --- reference style (S2 3.10 "Reference style" / manuscript checker) ---
    citation_style: Mapped[str | None] = mapped_column(String(64))

    # --- MANDATORY provenance (S2 L719) ---
    rule_source: Mapped[str] = mapped_column(Text, nullable=False)
    rule_verified_at: Mapped[date] = mapped_column(Date, nullable=False)
    verified_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    # Warn in the UI when older than this. Not enforced -- a stale-but-real rule is
    # still better than no rule, but it must be visible.
    stale_after_days: Mapped[int] = mapped_column(Integer, default=365, server_default="365")
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    @property
    def is_stale(self) -> bool:
        from datetime import timedelta

        return date.today() > self.rule_verified_at + timedelta(days=self.stale_after_days)

    @property
    def days_since_verified(self) -> int:
        return (date.today() - self.rule_verified_at).days
