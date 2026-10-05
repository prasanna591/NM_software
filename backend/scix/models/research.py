"""Research layer: StatisticalAnalysis, AnalysisParameter.

Source: S2 3.6-3.8, docs/06-integrity-authorship.md.

This is the integrity-critical entity. Every figure, significance annotation and reported
p-value traces to a row here, and the row records that the RESEARCHER selected it (R3).
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scix.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_col, optional_enum_col
from scix.models.enums import (
    Attributed,
    CurveFitModel,
    SignificanceMarker,
    StatisticalTestName,
)


class StatisticalAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One statistical run, chosen by the researcher.

    R3 (docs/01-product-vision.md 1.3): the system never produces statistical results on
    its own initiative. Enforced here by:
      * ``selected_by_id`` NOT NULL -- there is no default, no auto-pick, no "suggest a
        test" code path
      * ``test_name`` NOT NULL with no sentinel meaning "none"
      * ``significance_level`` is a per-analysis field, not a global constant, so
        changing a global default can never alter what an existing figure reports (Q18)

    ``library`` + ``library_version`` are NOT NULL because S2 3.13 reproducibility requires
    that a result be re-derivable. A p-value without the SciPy version that produced it
    is not a reproducible result.
    """

    __tablename__ = "statistical_analyses"
    __table_args__ = (
        Index("ix_statistical_analyses_project_created", "project_id", "created_at"),
        UniqueConstraint(
            "worksheet_id", "seq", name="uq_statistical_analyses_worksheet_seq"
        ),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    worksheet_id: Mapped[str] = mapped_column(
        ForeignKey("worksheets.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    test_name: Mapped[StatisticalTestName] = enum_col(StatisticalTestName, "test_name")
    library: Mapped[str] = mapped_column(String(64), nullable=False)
    library_version: Mapped[str] = mapped_column(String(32), nullable=False)

    # Column references, group structure, test-specific options.
    inputs: Mapped[dict] = mapped_column(default=dict, nullable=False)
    # Full result payload: test statistic, df, p-value, F, effect sizes, confidence
    # intervals, residuals, per-group descriptives.
    results: Mapped[dict] = mapped_column(default=dict, nullable=False)

    posthoc_test: Mapped[StatisticalTestName | None] = optional_enum_col(StatisticalTestName, "test_name_posthoc")
    significance_level: Mapped[float] = mapped_column(
        Float, default=0.05, server_default="0.05", nullable=False
    )

    # Curve fitting (S2 3.6). Null unless test_name is CURVE_FIT.
    fit_model: Mapped[CurveFitModel | None] = optional_enum_col(CurveFitModel, "curve_fit_model")
    fit_equation: Mapped[str | None] = mapped_column(Text)

    # Provenance -- which library the caller wants reported, not which produced the math.
    # The render/export service pins its own version separately.
    attribution: Mapped[Attributed] = enum_col(
        Attributed, "attributed_analysis", server_default="SOFTWARE"
    )
    selected_by_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    parameters: Mapped[list["AnalysisParameter"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class AnalysisParameter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Discrete reported values from a run.

    S2 3.6 requires nine outputs per curve fit: equation, R^2, adjusted R^2, residuals,
    confidence interval, parameter estimates, standard error, p-value. Large blobs
    (residuals, CI arrays) stay in ``StatisticalAnalysis.results``; this table holds the
    scalar values a manuscript actually cites, queryable without JSON extraction.
    """

    __tablename__ = "analysis_parameters"

    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("statistical_analyses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    # Rendered form, e.g. "t(28) = 2.045, p = 0.032"
    label: Mapped[str | None] = mapped_column(String(512))
    ordinal: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    __table_args__ = (
        UniqueConstraint("analysis_id", "name", name="uq_analysis_parameters_analysis_name"),
    )

    analysis: Mapped[StatisticalAnalysis] = relationship(back_populates="parameters")
