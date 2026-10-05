"""API request/response schemas.

These are the contract the frontend codes against, so they are written to be *stable and
explicit* rather than to mirror the ORM exactly. Two rules:

* Every response carries the identifiers the UI needs to make its next call. A frontend
  that has to re-list a collection to learn an id is a frontend that will drift.
* Enum-valued fields are the same strings the PostgreSQL enums store, so a value that
  validates here cannot fail at INSERT. ``StatisticalTestName.value`` is e.g.
  ``"one_way_anova"`` -- identical to the wire form used by ``graph_type`` and the
  profile YAML.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from scix.models.enums import (
    AuditCheckCode,
    AuditSeverity,
    ColumnDataType,
    GraphType,
    SignificanceMarker,
    StatisticalTestName,
    TargetKind,
    TransformType,
)

# --- common ------------------------------------------------------------------ #


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str
    warnings: list[str] = Field(default_factory=list)


# --- disciplines -------------------------------------------------------------- #


class DisciplineBrief(ORMModel):
    id: uuid.UUID
    key: str
    display_name: str
    description: str | None = None


class StatisticalMethodBrief(BaseModel):
    test: str
    label: str
    default_alpha: float
    post_hoc: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    guidance: str | None = None


class PlotCapabilityBrief(BaseModel):
    graph_type: str
    label: str
    rationale: str | None = None
    default: bool = False


class DisciplineDetail(DisciplineBrief):
    """What the wizard needs to configure itself for a discipline."""

    terminology_rule_count: int
    manuscript_templates: list[dict[str, Any]]
    statistical_methods: list[StatisticalMethodBrief]
    plot_capabilities: list[PlotCapabilityBrief]
    journal_requirements: list[dict[str, Any]]
    style_defaults: dict[str, Any]
    content_hash: str


# --- projects ----------------------------------------------------------------- #


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    discipline_id: uuid.UUID | None = None
    target_journal_id: uuid.UUID | None = None


class ProjectOut(ORMModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None = None
    discipline_id: uuid.UUID | None = None
    target_journal_id: uuid.UUID | None = None
    created_at: datetime
    dataset_count: int = 0
    graph_count: int = 0
    analysis_count: int = 0


# --- datasets / worksheets / columns ------------------------------------------ #


class WorksheetOut(ORMModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    ordinal: int
    row_count: int | None = None
    transform_seq: int


class ColumnOut(ORMModel):
    id: uuid.UUID
    worksheet_id: uuid.UUID
    ordinal: int
    name: str
    unit: str | None = None
    data_type: ColumnDataType
    role_x: bool
    role_y: bool
    is_replicate: bool
    group_name: str | None = None
    error_column_id: uuid.UUID | None = None
    formula: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
    statistics: dict[str, Any] | None = None


class ColumnPatch(BaseModel):
    """S2 3.3 per-column capabilities. Roles are independent and composable, so each is
    its own optional field -- PATCHing ``role_y`` must never clear ``is_replicate``."""

    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=64)
    data_type: ColumnDataType | None = None
    role_x: bool | None = None
    role_y: bool | None = None
    is_replicate: bool | None = None
    group_name: str | None = None
    error_column_id: uuid.UUID | None = None
    formula: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class DatasetOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_filename: str
    content_hash: str | None = None
    file_size_bytes: int | None = None
    row_count: int | None = None
    column_count: int | None = None
    sheet_names: list[str] | None = None
    created_at: datetime
    worksheets: list[WorksheetOut] = Field(default_factory=list)


class WorksheetDetail(ORMModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    ordinal: int
    row_count: int | None = None
    transform_seq: int
    columns: list[ColumnOut] = Field(default_factory=list)


# --- worksheet preview (ADR 0001: values live in Parquet, not in Postgres) ------- #


class ColumnPreview(BaseModel):
    column_id: uuid.UUID
    name: str
    data_type: str
    unit: str | None = None
    values: list[Any] = Field(default_factory=list)
    # Rows dropped because they were blank/non-numeric. Surfaced, never silently filled.
    non_numeric_count: int = 0


class WorksheetPreview(BaseModel):
    worksheet_id: uuid.UUID
    name: str
    row_count: int
    columns: list[ColumnPreview]
    truncated: bool


# --- transformations (IRREVERSIBLE: ordered, replayable) ---------------------- #


class TransformationOut(ORMModel):
    id: uuid.UUID
    worksheet_id: uuid.UUID
    seq: int
    transform_type: TransformType
    params: dict[str, Any]
    input_columns: list[str] | None = None
    output_columns: list[str] | None = None
    rows_before: int | None = None
    rows_after: int | None = None
    applied_by_id: uuid.UUID | None = None
    applied_at: datetime | None = None


class TransformationCreate(BaseModel):
    transform_type: TransformType
    params: dict[str, Any] = Field(default_factory=dict)
    column_names: list[str] = Field(default_factory=list)
    output_name: str | None = None


class TransformationChain(BaseModel):
    """S2 3.13 "Processing: Normalization -> Log transformation"."""


# --- statistics --------------------------------------------------------------- #


class AnalysisRequest(BaseModel):
    """``test_name`` is REQUIRED and has no "none" sentinel (R3).

    The wizard's Step 3 offers "None", but that is a UI choice meaning *do not run an
    analysis*, not a test value. A graph without an analysis simply has no
    ``source_analysis_id``.
    """

    worksheet_id: uuid.UUID
    test_name: StatisticalTestName
    significance_level: float = Field(default=0.05, gt=0.0, lt=1.0)
    y_columns: list[str] = Field(default_factory=list)
    group_column: str | None = None
    x_column: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class ParameterOut(ORMModel):
    name: str
    value: str
    label: str | None = None


class AnalysisOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    worksheet_id: uuid.UUID
    seq: int
    test_name: StatisticalTestName
    library: str
    library_version: str
    inputs: dict[str, Any]
    results: dict[str, Any]
    posthoc_test: StatisticalTestName | None = None
    significance_level: float
    selected_by_id: uuid.UUID
    created_at: datetime
    parameters: list[ParameterOut] = Field(default_factory=list)


# --- graphs ------------------------------------------------------------------- #


class AxisIn(BaseModel):
    axis: Literal["x", "y"]
    title: str | None = None
    unit: str | None = None
    scale: str = "linear"
    label_present: bool = True


class SeriesIn(BaseModel):
    name: str
    y_column: str
    x_column: str | None = None
    error_column: str | None = None
    error_basis: str = "none"


class GraphCreate(BaseModel):
    """The output of wizard steps 1-3. Step 4 hands this to the editor."""

    worksheet_id: uuid.UUID
    graph_type: GraphType
    name: str | None = None
    series: list[SeriesIn]
    axes: list[AxisIn] = Field(default_factory=list)
    source_analysis_id: uuid.UUID | None = None
    width_mm: float | None = 85.0
    height_mm: float | None = 65.0
    dpi: int = 600


class GraphPatch(BaseModel):
    name: str | None = None
    graph_type: GraphType | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    dpi: int | None = None
    background: str | None = None
    border: bool | None = None
    source_analysis_id: uuid.UUID | None = None


class AxisOut(ORMModel):
    axis: str
    title: str | None = None
    unit: str | None = None
    scale: str
    label_present: bool


class SeriesOut(ORMModel):
    id: uuid.UUID
    name: str
    x_column_id: uuid.UUID | None = None
    y_column_id: uuid.UUID | None = None
    error_basis: str


class GraphOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    graph_type: GraphType
    name: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    dpi: int
    source_analysis_id: uuid.UUID | None = None
    series: list[SeriesOut] = Field(default_factory=list)
    axes: list[AxisOut] = Field(default_factory=list)
    created_at: datetime


# --- render spec (ADR 0003: Matplotlib is authority, Plotly is preview) --------- #


class RenderSeries(BaseModel):
    name: str
    x: list[float | None]
    y: list[float | None]
    color: str | None = None
    line_style: str | None = None
    symbol: str | None = None
    # Error bars are part of the spec, not a renderer detail. S2 3.12 makes
    # "error bars identified" a blocking-integrity check, and the twelve-point audit asks
    # "are these values actually in the figure?" -- which is only answerable if the values
    # and the basis (SD / SEM / CI) reach the renderer. Declaring these also stops Pydantic
    # silently discarding them from the service's dict, which is what happened before.
    error_y: list[float | None] | None = None
    error_basis: str | None = None


class RenderSpec(BaseModel):
    """A pure function of the graph row -- what both renderers consume.

    The frontend draws this with Plotly for preview. The export service feeds the SAME
    spec to Matplotlib. Neither renderer owns state, which is what makes "same figure +
    same version = same output" achievable (docs/04 4.7).
    """

    graph_id: uuid.UUID
    graph_type: GraphType
    width_mm: float
    height_mm: float
    dpi: int
    background: str | None = None
    series: list[RenderSeries]
    x_axis: AxisOut | None = None
    y_axis: AxisOut | None = None
    legend: bool = True
    renderer_note: str = (
        "Preview only. Authoritative output is rendered server-side by Matplotlib (ADR 0003)."
    )


# --- figure audit (S2 3.12: the 12 checks) ------------------------------------- #


class AuditItem(BaseModel):
    code: AuditCheckCode
    label: str
    passed: bool
    severity: AuditSeverity
    detail: str
    # What the researcher must DO, not merely what is wrong.
    remedy: str | None = None


class FigureAuditOut(BaseModel):
    graph_id: uuid.UUID
    ran_at: datetime
    passed_count: int
    total_count: int
    blocking: bool
    items: list[AuditItem]


# --- provenance / trace (S2 3.13) --------------------------------------------- #


class ProvenanceField(BaseModel):
    label: str
    value: str | None = None
    # Clickable targets make Trace bidirectional rather than a text summary.
    link_type: Literal["dataset", "worksheet", "analysis", "graph", "figure", "user", "none"] = "none"
    link_id: uuid.UUID | None = None


class TransformationStep(BaseModel):
    seq: int
    transform_type: TransformType
    label: str
    params: dict[str, Any]
    applied_at: datetime | None = None


class ProvenanceOut(BaseModel):
    """Exactly the S2 3.13 panel, field for field."""

    figure_label: str
    source: ProvenanceField
    data: ProvenanceField
    processing: list[TransformationStep]
    analysis: ProvenanceField
    posthoc: ProvenanceField
    plot: ProvenanceField
    error: ProvenanceField
    created_by: ProvenanceField
    version: ProvenanceField
    completeness: Literal["complete", "partial", "minimal"]


# --- significance -------------------------------------------------------------- #


class SignificanceMarkerRequest(BaseModel):
    analysis_id: uuid.UUID
    marker: SignificanceMarker
    y_fraction: float | None = Field(default=None, ge=0.0, le=1.0)


# --- audit log ----------------------------------------------------------------- #


class AuditLogOut(ORMModel):
    id: int
    project_id: uuid.UUID
    attribution: str
    actor_user_id: uuid.UUID | None = None
    actor_component: str | None = None
    tool_version: str | None = None
    action: str
    target_type: TargetKind
    target_id: str | None = None
    before_value: dict[str, Any] | None = None
    after_value: dict[str, Any] | None = None
    detail: dict[str, Any] | None = None
    batch_id: str | None = None
    created_at: datetime


# --- journal presets ------------------------------------------------------------ #


class JournalPresetOut(ORMModel):
    id: uuid.UUID
    journal_name: str
    publisher: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    resolution_dpi: int | None = None
    file_format: str | None = None
    min_font_pt: float | None = None
    max_panels: int | None = None
    citation_style: str | None = None
    rule_source: str
    rule_verified_at: date
    stale_after_days: int
    notes: str | None = None


class JournalPresetDetail(JournalPresetOut):
    is_stale: bool
    days_since_verified: int


# --- terminology scan ----------------------------------------------------------- #


class TerminologyHit(BaseModel):
    rule_id: str
    kind: str
    severity: str
    description: str
    original: str
    suggested: str
    offset_start: int
    offset_end: int
    line_hint: int | None = None


class TerminologyVariant(BaseModel):
    """docs/07 7.6 GROUP step: one concept, the variants found, ranked by frequency."""

    rule_id: str
    kind: str
    variants: list[str]
    frequencies: list[int]
    suggested_canonical: str
    chosen_canonical: str | None = None


class TerminologyScanRequest(BaseModel):
    text: str
    discipline_key: str | None = None


class TerminologyScanOut(BaseModel):
    hits: list[TerminologyHit]
    variant_groups: list[TerminologyVariant]
    rules_evaluated: int


class ConsistencyApplyRequest(BaseModel):
    rule_id: str
    canonical: str
    hits: list[TerminologyHit]


# --- wizard options (S2 3.4 / 3.7) ---------------------------------------------- #


class GraphTypeOption(BaseModel):
    value: str
    label: str
    group: str


class TestOption(BaseModel):
    value: str
    label: str
    category: str
    description: str
    assumptions: list[str] = Field(default_factory=list)
    post_hoc: str | None = None
    requires_group_column: bool = False


class WizardOptions(BaseModel):
    """Everything Step 1-3 needs in one request.

    Fetched once so the wizard cannot offer a graph type or test the backend will later
    reject, and so the discipline profile can order and annotate the options.
    """

    disciplines: list[DisciplineBrief]
    graph_types: list[GraphTypeOption]
    tests: list[TestOption]
    significance_markers: list[str]
    error_bases: list[str]


# --- current user ---------------------------------------------------------------- #


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    institution_id: uuid.UUID | None = None