"""Identity, projects and discipline profiles.

Source: docs/05-data-model.md 5.3; S1 L398-400; S2 L852-863.
Discipline profile is defined in docs/07-disciplines-terminology.md 7.1.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scix.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_col, optional_enum_col
from scix.models.enums import UserRole


class Institution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """S1 Stage 4 -- university accounts. Nullable on User so single-tenant
    deployments need no seed data."""

    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="institution")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    institution_id: Mapped[str | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL")
    )
    role: Mapped[UserRole] = enum_col(UserRole, "user_role", default=UserRole.RESEARCHER, server_default="RESEARCHER")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    institution: Mapped[Institution | None] = relationship(back_populates="users")
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")


class DisciplineProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per discipline.

    S1 L421: "Each discipline carries its own terminology, manuscript templates,
    statistical methods, and journal formats -- on the same shared SCIX core."

    All four of those are DATA (docs/07 7.1). This table is the registry; the content
    lives in profiles/*.yaml so adding a discipline never requires an application
    change. If a profile ever needs an `if` statement, the abstraction has failed.
    """

    __tablename__ = "discipline_profiles"

    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Absolute path to the YAML that defines terminology rules, manuscript template,
    # preferred tests, default graph types and candidate journal presets.
    profile_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- denormalised profile content -------------------------------------- #
    # The YAML file stays the source of truth. These columns exist so that a project can
    # resolve its discipline in one query, and -- via `content_hash` -- so that editing a
    # profile on disk is visible as a change rather than silently absorbed by a running
    # deployment. Nothing here is hand-edited.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    terminology_rules: Mapped[list] = mapped_column(default=list)
    manuscript_templates: Mapped[list] = mapped_column(default=list)
    statistical_methods: Mapped[list] = mapped_column(default=list)
    plot_capabilities: Mapped[list] = mapped_column(default=list)
    style_defaults: Mapped[dict] = mapped_column(default=dict)
    profile_summary: Mapped[dict] = mapped_column(default=dict)


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """S2 L849: "a project as the root of every record"."""

    __tablename__ = "projects"

    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    discipline_id: Mapped[str | None] = mapped_column(
        ForeignKey("discipline_profiles.id", ondelete="SET NULL"), index=True
    )
    target_journal_id: Mapped[str | None] = mapped_column(
        ForeignKey("journal_presets.id", ondelete="SET NULL")
    )

    owner: Mapped[User] = relationship(back_populates="projects")
    discipline: Mapped[DisciplineProfile | None] = relationship()


class Manuscript(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Absent from S2's schema; defined in ADR 0002 (Q10)."""

    __tablename__ = "manuscripts"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list | None] = mapped_column()
    current_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("manuscript_revisions.id", ondelete="SET NULL")
    )
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    sections: Mapped[list["Section"]] = relationship(
        back_populates="manuscript",
        cascade="all, delete-orphan",
        order_by="Section.ordinal",
    )


class Section(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Flat with ordinal + heading_level, not nested.

    ADR 0002: real editors and DOCX itself need linear document order for export, and
    heading hierarchy is recoverable from heading_level. The S1 STRUCTURE "heading
    hierarchy" check becomes a scan for skipped levels.
    """

    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("manuscript_id", "ordinal", name="uq_sections_manuscript_ordinal"),
        Index("ix_sections_manuscript_heading", "manuscript_id", "heading_level"),
    )

    manuscript_id: Mapped[str] = mapped_column(
        ForeignKey("manuscripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(512), nullable=False)
    heading_level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    body: Mapped[str] = mapped_column(Text, default="", server_default="")

    manuscript: Mapped[Manuscript] = relationship(back_populates="sections")


class ManuscriptRevision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Whole-manuscript JSONB snapshot.

    ADR 0002: a journal article is ~1e5 characters, so a full snapshot is cheap and
    makes diffs trivial. section_id is NULL for a full-manuscript revision.
    """

    __tablename__ = "manuscript_revisions"

    manuscript_id: Mapped[str] = mapped_column(
        ForeignKey("manuscripts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    section_id: Mapped[str | None] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE")
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(nullable=False)
    author_type: Mapped[str] = mapped_column(String(16), nullable=False)
    author_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    message: Mapped[str | None] = mapped_column(Text)



class ManuscriptTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """S1 names `tables`; the TABLES checker has four checks against it."""

    __tablename__ = "manuscript_tables"

    section_id: Mapped[str | None] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)
    column_headers: Mapped[list | None] = mapped_column()
    row_count: Mapped[int | None] = mapped_column(Integer)
    units: Mapped[str | None] = mapped_column(String(128))
    data: Mapped[list | None] = mapped_column()


class Reference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """R4: SCIX never generates a reference. Rows exist only from user input or
    from a registry response. See build strategy 11.7 -- verifying a user-supplied
    DOI against CrossRef is validation, not generation."""

    __tablename__ = "references"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    citation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[list | None] = mapped_column()
    year: Mapped[int | None] = mapped_column(Integer)
    journal: Mapped[str | None] = mapped_column(Text)
    volume: Mapped[str | None] = mapped_column(String(32))
    issue: Mapped[str | None] = mapped_column(String(32))
    pages: Mapped[str | None] = mapped_column(String(64))
    doi: Mapped[str | None] = mapped_column(String(255), index=True)
    url: Mapped[str | None] = mapped_column(String(1024))
    verification_status: Mapped[str] = mapped_column(
        String(32), default="unverified", server_default="unverified", nullable=False
    )
    registry: Mapped[str | None] = mapped_column(String(64))
    registry_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_supplied: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "citation_key", name="uq_references_project_citation_key"),
        Index("ix_references_project_doi", "project_id", "doi"),
    )


class CitationLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Explicit join, not a column on Section.

    ADR 0002: the S1 REFERENCES dimension requires three reconciliations -- missing,
    duplicate, unused -- and all three are set operations over citation links. Without
    an explicit link table "unused references" is undetectable.
    """

    __tablename__ = "citation_links"

    section_id: Mapped[str] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reference_id: Mapped[str] = mapped_column(
        ForeignKey("references.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Ordinal within the section, so "Citation numbering" (S1 checker) is checkable.
    ordinal: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    character_offset: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("section_id", "reference_id", name="uq_citation_links_section_ref"),
    )
