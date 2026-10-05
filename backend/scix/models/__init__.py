"""Model package. Importing this module registers every table on ``Base.metadata``.

Order matters only for readability -- SQLAlchemy resolves string-based relationships
lazily -- but the groups are listed in dependency order so the schema is easy to read
top to bottom.
"""
from scix.db.base import Base
from scix.models.data import Column, DataTransformation, Dataset, Worksheet
from scix.models.enums import (
    AnnotationKind,
    Attributed,
    AuditCheckCode,
    AuditSeverity,
    AxisScale,
    ColumnDataType,
    CurveFitModel,
    ErrorBasis,
    ExportFormat,
    FigureSizePreset,
    GraphType,
    ReferenceVerification,
    Register,
    SignificanceMarker,
    SuggestionDecisionKind,
    SuggestionStatus,
    TargetKind,
    StatisticalTestName,
    TransformType,
    UserRole,
    VoicePreference,
    WritingTool,
)
from scix.models.identity import (
    CitationLink,
    DisciplineProfile,
    Institution,
    Manuscript,
    ManuscriptRevision,
    ManuscriptTable,
    Project,
    Reference,
    Section,
    User,
)
from scix.models.integrity import AuditLog, Export, FigureAudit, Version
from scix.models.journal import JournalPreset
from scix.models.plot import (
    Figure,
    FigurePanel,
    Graph,
    GraphAnnotation,
    GraphAxis,
    GraphSeries,
    GraphTemplate,
)
from scix.models.research import AnalysisParameter, StatisticalAnalysis
from scix.models.writing import SuggestionDecision, SuggestionRejection, WritingSuggestion

__all__ = [
    "Base",
    # identity
    "Institution",
    "User",
    "DisciplineProfile",
    "Project",
    "Manuscript",
    "Section",
    "ManuscriptRevision",
    "ManuscriptTable",
    "Reference",
    "CitationLink",
    # data
    "Dataset",
    "Worksheet",
    "Column",
    "DataTransformation",
    # research
    "StatisticalAnalysis",
    "AnalysisParameter",
    # plot
    "Graph",
    "GraphSeries",
    "GraphAxis",
    "GraphAnnotation",
    "GraphTemplate",
    "Figure",
    "FigurePanel",
    # journal
    "JournalPreset",
    # integrity
    "AuditLog",
    "Version",
    "FigureAudit",
    "Export",
    # writing
    "WritingSuggestion",
    "SuggestionDecision",
    "SuggestionRejection",
]
