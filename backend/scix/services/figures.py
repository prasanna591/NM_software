"""The S2 3.12 twelve-point figure audit, and the S2 3.13 provenance record.

These two live together because they answer the same question from opposite ends. The
audit asks "is this figure ready to submit?"; provenance asks "where did every number in
it come from?" A figure can pass twelve checks and still be untraceable, or be perfectly
traceable and unreadable, so neither subsumes the other.

On check 12. The source presents "Y-axis unit has not been specified" as the *demo
failure state* -- it exists to show the checklist is live rather than decorative. So a
figure genuinely fails here, and the check is BLOCKING rather than a warning. The
reasoning matters: an unlabelled y-axis is not a style preference, it makes the figure
uninterpretable, and every journal in the profile seeds a minimum font size precisely
because unreadable output gets rejected.

On checks 6 and 7. They are the integrity pair. Recording "ANOVA" satisfies 6; check 7
requires that values were actually computed and that a ``StatisticalAnalysis`` row
exists. Together they are what stops a figure from claiming a method it never ran.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from scix.models import (
    Column,
    Dataset,
    Figure,
    FigureAudit,
    Graph,
    StatisticalAnalysis,
    User,
    Worksheet,
)
from scix.models.enums import (
    AuditCheckCode,
    AuditSeverity,
    GraphType,
    TargetKind,
    TransformType,
)
from scix.services import audit as audit_log

# S2 3.4 Step 2 groups the gallery into five rows. Reproduced so the wizard can present
# the same grouping the source describes.
GRAPH_TYPE_GROUPS: list[tuple[str, list[GraphType]]] = [
    ("XY & Trend", [GraphType.XY, GraphType.LINE, GraphType.SCATTER]),
    ("Comparison", [GraphType.COLUMN, GraphType.GROUPED, GraphType.BOX]),
    ("Distribution", [GraphType.VIOLIN, GraphType.HISTOGRAM, GraphType.HEATMAP]),
    ("Clinical & Diagnostic", [GraphType.SURVIVAL, GraphType.ROC, GraphType.DOSE_RESPONSE]),
    ("Spectroscopy & Chemistry", [GraphType.SPECTRUM, GraphType.KINETIC, GraphType.CALIBRATION]),
    ("Additional", [GraphType.BAR, GraphType.STACKED, GraphType.AREA, GraphType.CONTOUR]),
]

GRAPH_TYPE_LABELS = {
    GraphType.XY: "XY",
    GraphType.LINE: "Line",
    GraphType.SCATTER: "Scatter",
    GraphType.COLUMN: "Column",
    GraphType.BAR: "Bar",
    GraphType.GROUPED: "Grouped",
    GraphType.STACKED: "Stacked",
    GraphType.BOX: "Box Plot",
    GraphType.VIOLIN: "Violin",
    GraphType.HISTOGRAM: "Histogram",
    GraphType.AREA: "Area",
    GraphType.HEATMAP: "Heatmap",
    GraphType.CONTOUR: "Contour",
    GraphType.SURVIVAL: "Survival",
    GraphType.ROC: "ROC",
    GraphType.CALIBRATION: "Calibration",
    GraphType.SPECTRUM: "Spectrum",
    GraphType.KINETIC: "Kinetics",
    GraphType.DOSE_RESPONSE: "Dose Response",
}

# Tests whose value is legitimately a single series -- requiring a legend on them would
# train researchers to ignore check 10. Q12.
SINGLE_SERIES_TYPES = {
    GraphType.XY, GraphType.LINE, GraphType.SPECTRUM, GraphType.KINETIC,
    GraphType.CALIBRATION, GraphType.ROC, GraphType.SURVIVAL, GraphType.DOSE_RESPONSE,
}

# Analysis-free types. Demanding a statistical method for a single calibration curve
# would push researchers to run tests they do not need just to pass a checklist.
ANALYSIS_OPTIONAL_TYPES = {
    GraphType.XY, GraphType.LINE, GraphType.SPECTRUM, GraphType.HEATMAP,
    GraphType.CONTOUR, GraphType.CALIBRATION, GraphType.KINETIC,
}

MIN_DPI = 300
RECOMMENDED_DPI = 600


@dataclass
class CheckResult:
    code: AuditCheckCode
    label: str
    passed: bool
    severity: AuditSeverity
    detail: str
    remedy: str | None = None


def run_audit(session: Session, graph: Graph) -> list[CheckResult]:
    """Evaluate all twelve checks. Pure with respect to the database -- it reads, never writes."""
    results: list[CheckResult] = []

    worksheet, dataset = _resolve_data_source(session, graph)
    series = graph.series
    axes = {a.axis: a for a in graph.axes}
    x_axis = axes.get("x")
    y_axis = axes.get("y")
    analysis = session.get(StatisticalAnalysis, graph.source_analysis_id) if graph.source_analysis_id else None

    # 1 -- dataset connected
    results.append(
        CheckResult(
            AuditCheckCode.DATASET_CONNECTED,
            "Dataset connected",
            passed=dataset is not None,
            severity=AuditSeverity.BLOCKING,
            detail=(
                f"Source: {dataset.source_filename} / {worksheet.name}"
                if dataset and worksheet
                else "No dataset is linked to this figure"
            ),
            remedy=None if dataset else "Attach a dataset before exporting",
        )
    )

    # 2 -- x-axis assigned
    x_assigned = any(s.x_column_id for s in series)
    results.append(
        CheckResult(
            AuditCheckCode.X_AXIS_ASSIGNED,
            "X-axis assigned",
            passed=x_assigned or graph.graph_type in {GraphType.COLUMN, GraphType.BAR, GraphType.GROUPED, GraphType.BOX, GraphType.VIOLIN, GraphType.HISTOGRAM, GraphType.STACKED, GraphType.AREA},
            severity=AuditSeverity.BLOCKING,
            detail=(
                f"X axis from {sum(1 for s in series if s.x_column_id)} of {len(series)} series"
                if x_assigned
                else "No series references an X column"
            ),
            remedy=None if x_assigned else "Choose an X column in the graph's series settings",
        )
    )

    # 3 -- y-axis assigned
    y_assigned = any(s.y_column_id for s in series)
    results.append(
        CheckResult(
            AuditCheckCode.Y_AXIS_ASSIGNED,
            "Y-axis assigned",
            passed=y_assigned,
            severity=AuditSeverity.BLOCKING,
            detail=f"{sum(1 for s in series if s.y_column_id)} of {len(series)} series have a Y column",
            remedy=None if y_assigned else "Assign a Y column to at least one series",
        )
    )

    # 4 -- units specified
    units_present = [c.unit for c in _y_columns(session, series) if c and c.unit]
    y_units = y_axis.unit if y_axis else None
    units_ok = bool(y_units) or bool(units_present)
    results.append(
        CheckResult(
            AuditCheckCode.UNITS_SPECIFIED,
            "Units specified",
            passed=units_ok,
            severity=AuditSeverity.WARN,
            detail=(
                f"Axis unit: {y_units}" if y_units
                else (f"Column units: {', '.join(units_present)}" if units_present else "No units found")
            ),
            remedy=None if units_ok else "Set a unit on the Y axis or on the plotted column",
        )
    )

    # 5 -- error bars identified
    with_errors = [s for s in series if s.error_basis and s.error_basis.value != "none"]
    results.append(
        CheckResult(
            AuditCheckCode.ERROR_BARS_IDENTIFIED,
            "Error bars identified",
            passed=bool(with_errors),
            severity=AuditSeverity.WARN,
            detail=(
                f"{len(with_errors)} of {len(series)} series: "
                + ", ".join(f"{s.name} ({s.error_basis.value})" for s in with_errors)
                if with_errors
                else "No error bars. Replicate columns are marked in the data workspace; "
                     "assigning replicates is what enables mean±SD"
            ),
            remedy=None if with_errors else "Mark replicate columns and choose an error basis (SD, SEM or CI)",
        )
    )

    # 6 -- statistical method recorded
    method_ok = analysis is not None
    results.append(
        CheckResult(
            AuditCheckCode.STATISTICAL_METHOD_RECORDED,
            "Statistical method recorded",
            passed=method_ok or graph.graph_type in ANALYSIS_OPTIONAL_TYPES,
            severity=AuditSeverity.WARN if graph.graph_type in ANALYSIS_OPTIONAL_TYPES else AuditSeverity.BLOCKING,
            detail=(
                f"{analysis.test_name.value} (alpha={analysis.significance_level})"
                if analysis
                else (
                    "Not applicable for this graph type"
                    if graph.graph_type in ANALYSIS_OPTIONAL_TYPES
                    else "No analysis is attached"
                )
            ),
            remedy=None if method_ok else "Run a test in the statistics wizard and attach it to this figure",
        )
    )

    # 7 -- statistical values calculated  (the integrity pair with 6)
    results_payload = (analysis.results or {}) if analysis else {}
    has_values = bool(results_payload) and any(
        k in results_payload for k in ("p_value", "coefficient", "r_squared", "f_statistic", "t_statistic")
    )
    values_ok = has_values or graph.graph_type in ANALYSIS_OPTIONAL_TYPES
    results.append(
        CheckResult(
            AuditCheckCode.STATISTICAL_VALUES_CALCULATED,
            "Statistical values calculated",
            passed=values_ok,
            severity=AuditSeverity.BLOCKING,
            detail=(
                _values_summary(results_payload)
                if has_values
                else (
                    "Not applicable for this graph type"
                    if graph.graph_type in ANALYSIS_OPTIONAL_TYPES
                    else (
                        "A method is named but no values were computed"
                        if analysis
                        else "No analysis attached, so no values exist"
                    )
                )
            ),
            remedy=None if values_ok else (
                "Re-run the analysis -- a named method with no computed values cannot be reported"
                if analysis
                else "Run the analysis first"
            ),
        )
    )

    # 8 -- resolution
    dpi = graph.dpi or 0
    res_ok = dpi >= MIN_DPI
    res_severity = AuditSeverity.PASS if dpi >= RECOMMENDED_DPI else AuditSeverity.WARN
    results.append(
        CheckResult(
            AuditCheckCode.RESOLUTION_ACCEPTABLE,
            "Figure resolution acceptable",
            passed=res_ok,
            severity=res_severity,
            detail=(
                f"{dpi} DPI at {graph.width_mm}×{graph.height_mm} mm"
                + ("" if dpi >= RECOMMENDED_DPI else f" — below the {RECOMMENDED_DPI} DPI journal standard")
            ),
            remedy=None if res_ok else f"Set the figure resolution to at least {RECOMMENDED_DPI} DPI",
        )
    )

    # 9 -- axis labels present
    labels_ok = bool(x_axis and x_axis.label_present) and bool(y_axis and y_axis.label_present)
    results.append(
        CheckResult(
            AuditCheckCode.AXIS_LABELS_PRESENT,
            "Axis labels present",
            passed=labels_ok,
            severity=AuditSeverity.BLOCKING,
            detail=(
                f"x: {x_axis.title or '(untitled)'}, y: {y_axis.title or '(untitled)'}"
                if x_axis and y_axis
                else "One or both axes are not defined"
            ),
            remedy=None if labels_ok else "Add a title to both axes",
        )
    )

    # 10 -- legend present
    legend_needed = graph.graph_type not in SINGLE_SERIES_TYPES and len(series) > 1
    has_legend = any(s.name for s in series) if legend_needed else True
    results.append(
        CheckResult(
            AuditCheckCode.LEGEND_PRESENT,
            "Legend present",
            passed=has_legend,
            severity=AuditSeverity.WARN,
            detail=(
                "Single-series figure — legend not required"
                if not legend_needed
                else (f"{len(series)} named series" if has_legend else "Multiple series but no series names")
            ),
            remedy=None if has_legend else "Name each series so the legend can be built",
        )
    )

    # 11 -- figure number assigned
    figure_number = _figure_number_for(session, graph)
    results.append(
        CheckResult(
            AuditCheckCode.FIGURE_NUMBER_ASSIGNED,
            "Figure number assigned",
            passed=figure_number is not None,
            severity=AuditSeverity.WARN,
            detail=(
                f"Figure {figure_number.figure_number}" if figure_number
                else "This graph is not yet part of a numbered figure"
            ),
            remedy=None if figure_number else "Add this graph as a panel of a figure and assign its number",
        )
    )

    # 12 -- Y-axis unit specified  (the source's demo failure state)
    results.append(
        CheckResult(
            AuditCheckCode.Y_AXIS_UNIT_SPECIFIED,
            "Y-axis unit specified",
            passed=bool(y_units),
            severity=AuditSeverity.BLOCKING,
            detail=(
                f"Y axis unit: {y_units}"
                if y_units
                else "Y-axis unit has not been specified. The figure cannot be interpreted "
                     "by a reader without it, and every journal in the profile states a "
                     "minimum legible size."
            ),
            remedy=None if y_units else "Set the Y-axis unit in the axis properties",
        )
    )

    return results


def _values_summary(payload: dict[str, Any]) -> str:
    bits = []
    if "p_value" in payload:
        bits.append(f"p = {payload['p_value']:.4g}")
    if "f_statistic" in payload:
        bits.append(f"F = {payload['f_statistic']:.4g}")
    if "t_statistic" in payload:
        bits.append(f"t = {payload['t_statistic']:.4g}")
    if "r_squared" in payload and payload["r_squared"] is not None:
        bits.append(f"R² = {payload['r_squared']:.4g}")
    if "coefficient" in payload:
        bits.append(f"r = {payload['coefficient']:.4g}")
    return ", ".join(bits) or "Values present"


def _resolve_data_source(session: Session, graph: Graph):
    if not graph.series:
        return None, None
    column = session.get(Column, graph.series[0].y_column_id) if graph.series[0].y_column_id else None
    if column is None:
        return None, None
    worksheet = session.get(Worksheet, column.worksheet_id)
    dataset = session.get(Dataset, worksheet.dataset_id) if worksheet else None
    return worksheet, dataset


def _y_columns(session: Session, series) -> list[Column | None]:
    return [session.get(Column, s.y_column_id) if s.y_column_id else None for s in series]


def _figure_number_for(session: Session, graph: Graph) -> Figure | None:
    from scix.models import FigurePanel

    panel = session.query(FigurePanel).filter(FigurePanel.graph_id == graph.id).one_or_none()
    if panel is None:
        return None
    return session.get(Figure, panel.figure_id)


def audit_and_persist(
    session: Session,
    graph: Graph,
    *,
    actor: audit_log.Actor,
    blocking_threshold: bool = True,
) -> tuple[FigureAudit, list[CheckResult]]:
    """Run the audit, persist the run, and report whether export should be blocked.

    The three counts are stored separately rather than as a single pass/fail flag so the
    history can answer "was it blocked, or merely warned?" after the fact -- which is the
    difference between a warning the researcher may overrule and a defect they cannot.
    """
    checks = run_audit(session, graph)
    passed = sum(1 for c in checks if c.passed)
    blocking_failed = sum(
        1 for c in checks if c.severity is AuditSeverity.BLOCKING and not c.passed
    )
    warned = sum(1 for c in checks if c.severity is AuditSeverity.WARN and not c.passed)
    blocking = blocking_failed > 0 and blocking_threshold

    row = FigureAudit(
        graph_id=graph.id,
        project_id=graph.project_id,
        checks=[
            {
                "code": c.code.value,
                "label": c.label,
                "passed": c.passed,
                "severity": c.severity.value,
                "detail": c.detail,
                "remedy": c.remedy,
            }
            for c in checks
        ],
        passed_count=passed,
        warn_count=warned,
        blocking_count=blocking_failed,
    )
    session.add(row)
    session.flush()

    audit_log.record(
        session=session,
        project_id=graph.project_id,
        actor=actor,
        action="figure_audited",
        target_type=TargetKind.GRAPH,
        target_id=str(graph.id),
        after_value={
            "passed": passed,
            "total": len(checks),
            "warned": warned,
            "blocking_failures": blocking_failed,
            "blocking": blocking,
        },
    )
    return row, checks


# --------------------------------------------------------------------------- #
# S2 3.13 provenance / Trace
# --------------------------------------------------------------------------- #

TRANSFORM_LABELS = {
    TransformType.NORMALIZE: "Normalization",
    TransformType.LOG: "Log transformation",
    TransformType.FILTER: "Filter",
    TransformType.SORT: "Sort",
    TransformType.GROUP: "Group",
    TransformType.MERGE: "Merge",
    TransformType.CALCULATE_COLUMN: "Calculated column",
    TransformType.MISSING_VALUES: "Missing values",
    TransformType.UNIT_CONVERT: "Unit conversion",
}


def build_provenance(session: Session, graph: Graph) -> dict[str, Any]:
    """The S2 3.13 panel, field for field.

    DERIVED, never authored. The `provenance` column on ``figures`` stores this so it can
    be embedded at export time, but it is rebuilt from live rows on every request --
    otherwise a stale cache would be reported as provenance, which is the opposite of the
    feature's purpose.
    """
    from scix.services.chain import chain

    worksheet, dataset = _resolve_data_source(session, graph)
    analysis = session.get(StatisticalAnalysis, graph.source_analysis_id) if graph.source_analysis_id else None
    creator = session.get(User, graph.created_by_id) if graph.created_by_id else None
    figure = _figure_number_for(session, graph)

    steps = []
    if worksheet:
        for step in chain(session, worksheet.id):
            steps.append(
                {
                    "seq": step.seq,
                    "transform_type": step.transform_type.value,
                    "label": TRANSFORM_LABELS.get(step.transform_type, step.transform_type.value),
                    "params": {k: v for k, v in (step.params or {}).items() if not k.startswith("_")},
                    "applied_at": step.applied_at.isoformat() if step.applied_at else None,
                }
            )

    error_bases = sorted({s.error_basis.value for s in graph.series if s.error_basis and s.error_basis.value != "none"})

    fields = {
        "source": {
            "label": "Source",
            "value": dataset.source_filename if dataset else None,
            "link_type": "dataset" if dataset else "none",
            "link_id": str(dataset.id) if dataset else None,
        },
        "data": {
            "label": "Data",
            "value": worksheet.name if worksheet else None,
            "link_type": "worksheet" if worksheet else "none",
            "link_id": str(worksheet.id) if worksheet else None,
        },
        "analysis": {
            "label": "Analysis",
            "value": analysis.test_name.value if analysis else None,
            "link_type": "analysis" if analysis else "none",
            "link_id": str(analysis.id) if analysis else None,
        },
        "posthoc": {
            "label": "Post-hoc",
            "value": analysis.posthoc_test.value if analysis and analysis.posthoc_test else None,
            "link_type": "analysis" if analysis else "none",
            "link_id": str(analysis.id) if analysis else None,
        },
        "plot": {
            "label": "Plot",
            "value": GRAPH_TYPE_LABELS.get(graph.graph_type, graph.graph_type.value),
            "link_type": "graph",
            "link_id": str(graph.id),
        },
        "error": {"label": "Error", "value": ", ".join(error_bases) or None, "link_type": "none", "link_id": None},
        "created_by": {
            "label": "Created",
            "value": f"{creator.full_name}" if creator else (graph.name or "SCIX Plot Studio"),
            "link_type": "user" if creator else "none",
            "link_id": str(creator.id) if creator else None,
        },
        "version": {
            "label": "Version",
            "value": (analysis.library_version if analysis else None) or "v1.4",
            "link_type": "none",
            "link_id": None,
        },
    }

    present = [f for f in fields.values() if f["value"]]
    if not steps:
        completeness = "minimal" if len(present) <= 2 else "partial"
    elif len(present) >= 6:
        completeness = "complete"
    else:
        completeness = "partial"

    return {
        "figure_label": f"FIGURE {figure.figure_number}" if figure else (graph.name or "Untitled figure"),
        **fields,
        "processing": steps,
        "completeness": completeness,
    }


def trace_targets(session: Session, graph: Graph) -> dict[str, Any]:
    """Bidirectional links for the Trace action.

    S2 L779: Trace "returns to the underlying dataset and analysis". This returns every
    id the UI must navigate to, plus the state of the chain, so the trace panel can
    report a gap rather than silently jumping to the current state only.
    """
    from scix.services.chain import verify_chain

    worksheet, dataset = _resolve_data_source(session, graph)
    problems = []
    if worksheet:
        from scix.core.config import get_settings

        problems = verify_chain(session, worksheet, get_settings().storage_dir)

    return {
        "dataset_id": str(dataset.id) if dataset else None,
        "worksheet_id": str(worksheet.id) if worksheet else None,
        "analysis_id": str(graph.source_analysis_id) if graph.source_analysis_id else None,
        "graph_id": str(graph.id),
        "chain_length": worksheet.transform_seq if worksheet else 0,
        "chain_problems": problems,
        "traceable": not problems,
    }