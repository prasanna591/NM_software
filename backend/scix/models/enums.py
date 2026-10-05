"""Enumerations.

These are the registries the specification fixes. Where the source enumerates a set
(19 graph types, 21 statistical tests, 7 authorship/attribution values) it is reproduced
here exactly. Where it implies a set without listing it, the enum is the engineering
proposal and is marked as such.

Source: docs/05-data-model.md 5.5 (tests), 5.6 (graph types), docs/06-integrity-authorship.md
"""
from __future__ import annotations

import enum


class Attributed(enum.Enum):
    """Who performed an action. The two values the spec allows, and no others.

    docs/01-product-vision.md R5. The authorship panel (S1 L356-371) shows exactly
    these two badges. Adding a third value -- "ai", "assistant", "model" -- would
    break the product's central claim, so it is deliberately not extensible.
    """

    HUMAN = "human"
    SOFTWARE = "software"


class UserRole(enum.Enum):
    """S1 Stage 4. Single-tenant values are valid from Stage 1."""

    RESEARCHER = "researcher"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


# --------------------------------------------------------------------------- #
# Data layer -- S2 3
# --------------------------------------------------------------------------- #


class ColumnDataType(enum.Enum):
    NUMERIC = "numeric"
    TEXT = "text"
    DATE = "date"
    CATEGORICAL = "categorical"
    ORDINAL = "ordinal"  # Q13: Likert. Needed for the Social Sciences claim to be honest.


class TransformType(enum.Enum):
    """S2 3.3 data_transformations.

    An ordered log of these is what makes Trace Figure (S2 3.13) possible. The spec's
    own example is a two-step chain: "Normalization -> Log transformation".
    """

    NORMALIZE = "normalize"
    LOG = "log"
    FILTER = "filter"
    SORT = "sort"
    GROUP = "group"
    MERGE = "merge"
    CALCULATE_COLUMN = "calculate_column"
    MISSING_VALUES = "missing_values"
    UNIT_CONVERT = "unit_convert"


# --------------------------------------------------------------------------- #
# Research layer -- S2 3.7, docs/05-data-model.md 5.5
# --------------------------------------------------------------------------- #


class StatisticalTestName(enum.Enum):
    """The 21-test registry consolidated from S2 2 ANALYSIS, 3.4 Step 3 and 3.7."""

    DESCRIPTIVE_STATISTICS = "descriptive_statistics"
    T_TEST = "t_test"
    PAIRED_T_TEST = "paired_t_test"
    ONE_WAY_ANOVA = "one_way_anova"
    TWO_WAY_ANOVA = "two_way_anova"
    TUKEY = "tukey"
    MULTIPLE_COMPARISONS = "multiple_comparisons"
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    LINEAR_REGRESSION = "linear_regression"
    POLYNOMIAL_REGRESSION = "polynomial_regression"
    NONLINEAR_REGRESSION = "nonlinear_regression"
    DOSE_RESPONSE = "dose_response"
    SURVIVAL = "survival"
    KAPLAN_MEIER = "kaplan_meier"
    ROC = "roc"
    TIME_SERIES = "time_series"
    MULTIVARIATE = "multivariate"
    CHI_SQUARE = "chi_square"
    CURVE_FIT = "curve_fit"
    CUSTOM = "custom"


class CurveFitModel(enum.Enum):
    """S2 3.6 -- 9 model families."""

    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    POWER = "power"
    GAUSSIAN = "gaussian"
    LORENTZIAN = "lorentzian"
    SIGMOIDAL = "sigmoidal"
    CUSTOM = "custom"


class SignificanceMarker(enum.Enum):
    """S2 3.8 marker vocabulary. Both star notation and explicit p-values."""

    STAR_1 = "*"
    STAR_2 = "**"
    STAR_3 = "***"
    STAR_4 = "****"
    NS = "ns"
    P_EXACT = "p_exact"
    P_LESS_THAN = "p_lt"


# --------------------------------------------------------------------------- #
# Plot layer -- S2 3.2, docs/05-data-model.md 5.6
# --------------------------------------------------------------------------- #


class GraphType(enum.Enum):
    """The 19-type registry consolidated from S2 PLOT menu, wizard Step 2 and 3.8."""

    XY = "xy"
    LINE = "line"
    SCATTER = "scatter"
    COLUMN = "column"
    BAR = "bar"
    GROUPED = "grouped"
    STACKED = "stacked"
    BOX = "box"
    VIOLIN = "violin"
    HISTOGRAM = "histogram"
    AREA = "area"
    HEATMAP = "heatmap"
    CONTOUR = "contour"
    SURVIVAL = "survival"
    ROC = "roc"
    CALIBRATION = "calibration"
    SPECTRUM = "spectrum"
    KINETIC = "kinetic"
    DOSE_RESPONSE = "dose_response"


class AxisScale(enum.Enum):
    LINEAR = "linear"
    LOG = "log"
    LOGLOG = "loglog"
    SEMILOGX = "semilogx"
    SEMILOGY = "semilogy"
    CATEGORICAL = "categorical"


class ErrorBasis(enum.Enum):
    """S2 3.13 provenance field "Error: SD"."""

    SD = "sd"
    SEM = "sem"
    CI = "ci"
    NONE = "none"


class AnnotationKind(enum.Enum):
    """S2 3.5 left toolbar. SIGNIFICANCE is constrained to require an analysis."""

    TEXT = "text"
    ARROW = "arrow"
    LINE = "line"
    SHAPE = "shape"
    SIGNIFICANCE = "significance"


class FigureSizePreset(enum.Enum):
    """S2 3.9."""

    SINGLE_COLUMN = "single_column"
    ONE_POINT_FIVE_COLUMN = "one_point_five_column"
    DOUBLE_COLUMN = "double_column"
    CUSTOM = "custom"


# --------------------------------------------------------------------------- #
# Validation / integrity -- S2 3.12, docs/06-integrity-authorship.md
# --------------------------------------------------------------------------- #


class AuditSeverity(enum.Enum):
    """Q12. Default WARN because hard-blocking "legend present" is wrong for a
    single-series figure. UNITS_SPECIFIED and STATISTICAL_VALUES_CALCULATED are the
    only candidates for BLOCKING."""

    PASS = "pass"
    WARN = "warn"
    BLOCKING = "blocking"


class AuditCheckCode(enum.Enum):
    """The 12 checks of S2 3.12, verbatim."""

    DATASET_CONNECTED = "dataset_connected"
    X_AXIS_ASSIGNED = "x_axis_assigned"
    Y_AXIS_ASSIGNED = "y_axis_assigned"
    UNITS_SPECIFIED = "units_specified"
    ERROR_BARS_IDENTIFIED = "error_bars_identified"
    STATISTICAL_METHOD_RECORDED = "statistical_method_recorded"
    STATISTICAL_VALUES_CALCULATED = "statistical_values_calculated"
    RESOLUTION_ACCEPTABLE = "resolution_acceptable"
    AXIS_LABELS_PRESENT = "axis_labels_present"
    LEGEND_PRESENT = "legend_present"
    FIGURE_NUMBER_ASSIGNED = "figure_number_assigned"
    Y_AXIS_UNIT_SPECIFIED = "y_axis_unit_specified"


class ExportFormat(enum.Enum):
    """S2 3.15 export engine + S1 API surface."""

    DOCX = "docx"
    PDF = "pdf"
    LATEX = "latex"
    PPTX = "pptx"
    PNG = "png"
    TIFF = "tiff"
    JPEG = "jpeg"
    SVG = "svg"
    EPS = "eps"


# --------------------------------------------------------------------------- #
# Writing layer -- ADR 0002
# --------------------------------------------------------------------------- #


class WritingTool(enum.Enum):
    """The six S1 2.2-2.7 writing tools."""

    GRAMMAR = "grammar"
    SENTENCE = "sentence"
    REGISTER = "register"
    PARAGRAPH = "paragraph"
    TERMINOLOGY = "terminology"
    CONSISTENCY = "consistency"


class SuggestionStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SuggestionDecisionKind(enum.Enum):
    """R6. The three actions of S1 L253-257.

    Named ``...Kind`` to match the native Postgres type and to leave the bare name
    ``SuggestionDecision`` free for the ORM class in ``writing.py``. Two different
    things sharing one name in the same module is how the enum silently became the
    relationship target.
    """

    ACCEPT = "accept"
    EDIT = "edit"
    REJECT = "reject"


class Register(enum.Enum):
    """S1 2.4 -- "as selectable options", so each is an independent choice."""

    ACADEMIC = "academic"
    CONCISE = "concise"
    FORMAL = "formal"


class VoicePreference(enum.Enum):
    KEEP = "keep"
    ACTIVE = "active"
    PASSIVE = "passive"


class ReferenceVerification(enum.Enum):
    """R4 -- SCIX never generates a reference. It can only verify one the user
    supplied against an authoritative registry (build strategy 11.7)."""

    UNVERIFIED = "unverified"
    DOI_RESOLVES = "doi_resolves"
    REGISTRY_VERIFIED = "registry_verified"


class TargetKind(enum.Enum):
    """What an audit row or version refers to.

    Every entity type that can be the subject of a recorded action needs a member here,
    because ``audit_logs.target_type`` is a native enum: an unlisted target is not a
    rejected string, it is a schema that cannot represent the history it is being asked
    to keep.
    """

    MANUSCRIPT = "manuscript"
    SECTION = "section"
    FIGURE = "figure"
    GRAPH = "graph"
    TABLE = "table"
    DATASET = "dataset"
    WORKSHEET = "worksheet"
    COLUMN = "column"
    DATA_TRANSFORMATION = "data_transformation"
    ANALYSIS = "analysis"
    PROJECT = "project"
    EXPORT = "export"
    JOURNAL_PRESET = "journal_preset"
    DISCIPLINE_PROFILE = "discipline_profile"
    GRAPH_TEMPLATE = "graph_template"
