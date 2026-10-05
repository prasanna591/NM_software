"""Plot layer: Graph, GraphSeries, GraphAxis, GraphAnnotation, GraphTemplate, Figure, FigurePanel.

Source: S2 3.1-3.11.

INVARIANT (R3, S2 3.8): ``GraphAnnotation.source_analysis_id`` is NOT NULL when
``kind = 'significance'``. This is what makes "derived only from the analysis actually
run" true rather than aspirational -- the system cannot draw a significance bracket
without a backing analysis row whose p-value generated the marker.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scix.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_col, optional_enum_col
from scix.models.enums import (
    AnnotationKind,
    Attributed,
    AxisScale,
    ErrorBasis,
    FigureSizePreset,
    GraphType,
    SignificanceMarker,
)


class Graph(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single plot. The canonical ``graph_spec`` of ADR 0003.

    Both renderers -- Plotly for preview, Matplotlib for authoritative output -- are
    pure functions of this row plus its series and axes. Neither holds state.
    """

    __tablename__ = "graphs"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    graph_type: Mapped[GraphType] = enum_col(GraphType, "graph_type")
    name: Mapped[str | None] = mapped_column(String(255))

    width_mm: Mapped[float | None] = mapped_column(Float)
    height_mm: Mapped[float | None] = mapped_column(Float)
    # S2 3.9 worked example: 600 DPI. ADR 0003 default.
    dpi: Mapped[int] = mapped_column(Integer, default=600, server_default="600")

    background: Mapped[str | None] = mapped_column(String(32))
    border: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    panel_layout: Mapped[dict | None] = mapped_column()

    # The analysis this graph visualises, if any. Feeds "Statistical method recorded"
    # and "Statistical values calculated" in the S2 3.12 figure audit.
    source_analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("statistical_analyses.id", ondelete="SET NULL"), index=True
    )

    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    __table_args__ = (
        CheckConstraint("dpi > 0", name="dpi_positive"),
        CheckConstraint(
            "width_mm IS NULL OR width_mm > 0", name="width_positive"
        ),
        CheckConstraint(
            "height_mm IS NULL OR height_mm > 0", name="height_positive"
        ),
    )

    series: Mapped[list["GraphSeries"]] = relationship(
        back_populates="graph", cascade="all, delete-orphan"
    )
    axes: Mapped[list["GraphAxis"]] = relationship(
        back_populates="graph", cascade="all, delete-orphan"
    )
    annotations: Mapped[list["GraphAnnotation"]] = relationship(
        back_populates="graph", cascade="all, delete-orphan"
    )


class GraphSeries(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One plotted series. S2 3.5 right panel "Series" group."""

    __tablename__ = "graph_series"
    __table_args__ = (
        UniqueConstraint("graph_id", "name", name="uq_graph_series_graph_name"),
        Index("ix_graph_series_graph_ordinal", "graph_id", "ordinal"),
    )

    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    x_column_id: Mapped[str | None] = mapped_column(ForeignKey("columns.id", ondelete="RESTRICT"))
    y_column_id: Mapped[str | None] = mapped_column(ForeignKey("columns.id", ondelete="RESTRICT"))
    error_column_id: Mapped[str | None] = mapped_column(
        ForeignKey("columns.id", ondelete="SET NULL")
    )
    error_basis: Mapped[ErrorBasis] = enum_col(ErrorBasis, "error_basis", default=ErrorBasis.NONE, server_default="NONE")

    symbol: Mapped[str | None] = mapped_column(String(32))
    line_style: Mapped[str | None] = mapped_column(String(32))
    size: Mapped[float | None] = mapped_column(Float)
    color: Mapped[str | None] = mapped_column(String(32))
    transparency: Mapped[float | None] = mapped_column(Float)

    graph: Mapped[Graph] = relationship(back_populates="series")


class GraphAxis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """S2 3.5 right panel "X / Y Axis" group.

    ``unit`` and ``label_present`` exist because the S2 3.12 audit checks "Units
    specified", "Axis labels present" and -- the failure state shown in the source --
    "Y-axis unit has not been specified".
    """

    __tablename__ = "graph_axes"
    __table_args__ = (
        UniqueConstraint("graph_id", "axis", name="uq_graph_axes_graph_axis"),
    )

    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    axis: Mapped[str] = mapped_column(String(4), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(64))
    scale: Mapped[AxisScale] = enum_col(AxisScale, "axis_scale", default=AxisScale.LINEAR, server_default="LINEAR")
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    major_interval: Mapped[float | None] = mapped_column(Float)
    minor_interval: Mapped[float | None] = mapped_column(Float)
    label_present: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    graph: Mapped[Graph] = relationship(back_populates="axes")


class GraphAnnotation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canvas annotations, including significance markers.

    S2 3.8: markers are "derived only from the analysis actually run". The CHECK
    constraint below makes that a database guarantee rather than a code convention --
    there is no INSERT that can produce an unsupported significance marker.
    """

    __tablename__ = "graph_annotations"
    __table_args__ = (
        CheckConstraint(
            "(kind <> 'SIGNIFICANCE') OR (source_analysis_id IS NOT NULL)",
            name="significance_requires_analysis",
    ),
        Index("ix_graph_annotations_graph_kind", "graph_id", "kind"),
    )

    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[AnnotationKind] = enum_col(AnnotationKind, "annotation_kind")
    content: Mapped[str | None] = mapped_column(Text)
    marker: Mapped[SignificanceMarker | None] = optional_enum_col(
        SignificanceMarker, "significance_marker"
    )
    x_value: Mapped[float | None] = mapped_column(Float)
    y_value: Mapped[float | None] = mapped_column(Float)
    x_fraction: Mapped[float | None] = mapped_column(Float)
    y_fraction: Mapped[float | None] = mapped_column(Float)
    style: Mapped[dict | None] = mapped_column()

    source_analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("statistical_analyses.id", ondelete="RESTRICT")
    )
    attribution: Mapped[Attributed] = enum_col(
        Attributed, "attributed_annotation", server_default="SOFTWARE"
    )
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    graph: Mapped[Graph] = relationship(back_populates="annotations")


class GraphTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """S2 3.11 -- 10 starter templates, user-customisable and persistable.

    ``project_id`` NULL means a system template. Templates are a first-class entity,
    not a hardcoded list, because S2 L725 says they are "reusable, discipline-independent
    starting points that researchers can customize and save".
    """

    __tablename__ = "graph_templates"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    discipline_key: Mapped[str | None] = mapped_column(String(64), index=True)
    graph_spec: Mapped[dict] = mapped_column(nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Figure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A submission-ready multi-panel figure. S2 3.9."""

    __tablename__ = "figures"
    __table_args__ = (
        UniqueConstraint("project_id", "figure_number", name="uq_figures_project_number"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    figure_number: Mapped[str | None] = mapped_column(String(64), index=True)
    caption: Mapped[str | None] = mapped_column(Text)

    size_preset: Mapped[FigureSizePreset] = enum_col(
        FigureSizePreset, "figure_size_preset", default=FigureSizePreset.SINGLE_COLUMN,
        server_default="SINGLE_COLUMN",
    )
    width_mm: Mapped[float] = mapped_column(Float, default=85.0, server_default="85")
    height_mm: Mapped[float] = mapped_column(Float, default=65.0, server_default="65")
    dpi: Mapped[int] = mapped_column(Integer, default=600, server_default="600")
    journal_preset_id: Mapped[str | None] = mapped_column(
        ForeignKey("journal_presets.id", ondelete="SET NULL")
    )

    # S2 3.13 reproducibility record. DERIVED, never authored -- see
    # services/provenance.py. Stored for export-time embedding, refreshed on every
    # change to any contributing graph.
    provenance: Mapped[dict | None] = mapped_column()
    provenance_refreshed_at: Mapped[str | None] = mapped_column(String(64))

    panels: Mapped[list["FigurePanel"]] = relationship(
        back_populates="figure", cascade="all, delete-orphan", order_by="FigurePanel.ordinal"
    )


class FigurePanel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """S2 3.9 -- graphs dragged into panels, aligned automatically, auto-lettered."""

    __tablename__ = "figure_panels"

    figure_id: Mapped[str] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), index=True, nullable=False
    )
    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    panel_label: Mapped[str | None] = mapped_column(String(8))
    grid_row: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    grid_col: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    figure: Mapped[Figure] = relationship(back_populates="panels")
