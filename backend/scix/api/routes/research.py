"""Statistics, graph, significance, audit and provenance routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from scix.api.deps import get_current_user, require_project
from scix.core.config import get_settings
from scix.db.session import get_db
from scix.models import (
    Column,
    Dataset,
    Graph,
    GraphAnnotation,
    Project,
    StatisticalAnalysis,
    User,
    Worksheet,
)
from scix.models.enums import (
    AnnotationKind,
    Attributed,
    GraphType,
    SignificanceMarker,
    TargetKind,
)
from scix.schemas.api import (
    AnalysisOut,
    AnalysisRequest,
    AuditItem,
    AxisOut,
    AuditLogOut,
    FigureAuditOut,
    GraphCreate,
    GraphOut,
    GraphPatch,
    ParameterOut,
    ProvenanceField,
    ProvenanceOut,
    RenderSpec,
    SignificanceMarkerRequest,
    SeriesOut,
    TransformationStep,
)
from scix.services import audit as audit_log
from scix.services import figures as figure_service
from scix.services import render as render_service
from scix.services import statistics as stats_service

router = APIRouter()


def _worksheet_in_project(session: Session, worksheet_id: uuid.UUID, project: Project) -> Worksheet:
    worksheet = session.get(Worksheet, worksheet_id)
    if worksheet is None:
        raise HTTPException(status_code=404, detail="worksheet not found")
    dataset = session.get(Dataset, worksheet.dataset_id)
    if dataset is None or dataset.project_id != project.id:
        raise HTTPException(status_code=403, detail="worksheet belongs to another project")
    return worksheet


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #
@router.post("/statistics/analyze", response_model=AnalysisOut, status_code=201, tags=["statistics"])
def analyze(
    project_id: uuid.UUID,
    payload: AnalysisRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run the test the researcher selected. R3: there is no auto-select path.

    ``test_name`` is required and has no "none" sentinel -- a graph without an analysis
    simply carries no ``source_analysis_id``.
    """
    project = require_project(project_id, session=session, user=user)
    worksheet = _worksheet_in_project(session, payload.worksheet_id, project)

    try:
        outcome = stats_service.run(
            session,
            project_id=str(project.id),
            worksheet=worksheet,
            test_name=payload.test_name,
            selected_by_id=str(user.id),
            significance_level=payload.significance_level,
            y_columns=payload.y_columns,
            group_column=payload.group_column,
            x_column=payload.x_column,
            options=payload.options,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session.commit()
    session.refresh(outcome.analysis)

    out = _analysis_out(outcome.analysis)
    if outcome.warnings:
        out.results = {**out.results, "warnings": outcome.warnings}
    return out


@router.get("/statistics/analyses", response_model=list[AnalysisOut], tags=["statistics"])
def list_analyses(
    project_id: uuid.UUID,
    worksheet_id: uuid.UUID | None = None,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = require_project(project_id, session=session, user=user)
    stmt = select(StatisticalAnalysis).where(StatisticalAnalysis.project_id == project.id)
    if worksheet_id:
        stmt = stmt.where(StatisticalAnalysis.worksheet_id == worksheet_id)
    rows = session.execute(stmt.order_by(StatisticalAnalysis.created_at.desc())).scalars().all()
    return [_analysis_out(r) for r in rows]


@router.get("/statistics/analyses/{analysis_id}", response_model=AnalysisOut, tags=["statistics"])
def get_analysis(
    analysis_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    analysis = session.get(StatisticalAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    require_project(analysis.project_id, session=session, user=user)
    return _analysis_out(analysis)


@router.post("/statistics/analyses/{analysis_id}/posthoc", tags=["statistics"])
def posthoc(
    analysis_id: uuid.UUID,
    alpha: float = 0.05,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Post-hoc comparison against a stored omnibus test.

    Refuses anything other than a one-way ANOVA. A pairwise table with no omnibus test
    behind it is precisely the unsupported claim S2 3.8 forbids.
    """
    analysis = session.get(StatisticalAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    require_project(analysis.project_id, session=session, user=user)

    try:
        result = stats_service.posthoc_tukey(analysis, alpha=alpha)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result


# --------------------------------------------------------------------------- #
# graphs
# --------------------------------------------------------------------------- #
@router.post("/graphs/create", response_model=GraphOut, status_code=201, tags=["graphs"])
def create_graph(
    project_id: uuid.UUID,
    payload: GraphCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a graph from the wizard's steps 1-3 output. Step 4 edits it."""
    project = require_project(project_id, session=session, user=user)
    worksheet = _worksheet_in_project(session, payload.worksheet_id, project)

    columns = {c.name: c for c in worksheet.columns}
    for series in payload.series:
        for role, value in (("Y", series.y_column), ("X", series.x_column), ("error", series.error_column)):
            if value and value not in columns:
                raise HTTPException(
                    status_code=422,
                    detail=f"{role} column {value!r} is not in {worksheet.name}. Available: {sorted(columns)}",
                )

    if payload.source_analysis_id is not None:
        analysis = session.get(StatisticalAnalysis, payload.source_analysis_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="source analysis not found")
        if analysis.project_id != project.id:
            raise HTTPException(status_code=403, detail="analysis belongs to another project")

    settings = get_settings()
    graph = Graph(
        project_id=project.id,
        graph_type=payload.graph_type,
        name=payload.name or f"{payload.graph_type.value.title()} — {worksheet.name}",
        width_mm=payload.width_mm or settings.default_figure_width_mm,
        height_mm=payload.height_mm or settings.default_figure_height_mm,
        dpi=payload.dpi or settings.default_dpi,
        source_analysis_id=payload.source_analysis_id,
        created_by_id=user.id,
    )
    session.add(graph)
    session.flush()

    from scix.models import GraphAxis, GraphSeries
    from scix.models.enums import AxisScale, ErrorBasis

    for ordinal, s in enumerate(payload.series):
        session.add(
            GraphSeries(
                graph_id=graph.id,
                ordinal=ordinal,
                name=s.name,
                x_column_id=columns[s.x_column].id if s.x_column else None,
                y_column_id=columns[s.y_column].id if s.y_column else None,
                error_column_id=columns[s.error_column].id if s.error_column else None,
                error_basis=ErrorBasis(s.error_basis),
            )
        )
    for axis in payload.axes:
        session.add(
            GraphAxis(
                graph_id=graph.id,
                axis=axis.axis,
                title=axis.title,
                unit=axis.unit,
                scale=AxisScale(axis.scale),
                label_present=axis.label_present,
            )
        )

    audit_log.record(
        session=session,
        project_id=str(project.id),
        actor=audit_log.Actor.human(str(user.id)),
        action="graph_created",
        target_type=TargetKind.GRAPH,
        target_id=str(graph.id),
        after_value={
            "graph_type": payload.graph_type.value,
            "worksheet_id": str(worksheet.id),
            "series": [s.name for s in payload.series],
            "source_analysis_id": str(payload.source_analysis_id) if payload.source_analysis_id else None,
        },
    )

    session.commit()
    session.refresh(graph)
    return _graph_out(graph)


@router.get("/graphs", response_model=list[GraphOut], tags=["graphs"])
def list_graphs(
    project_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = require_project(project_id, session=session, user=user)
    rows = session.execute(
        select(Graph).where(Graph.project_id == project.id).order_by(Graph.created_at.desc())
    ).scalars().all()
    return [_graph_out(g) for g in rows]


@router.get("/graphs/{graph_id}", response_model=GraphOut, tags=["graphs"])
def get_graph(
    graph_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    graph = _require_graph(session, graph_id, user)
    return _graph_out(graph)


@router.patch("/graphs/{graph_id}", response_model=GraphOut, tags=["graphs"])
def patch_graph(
    graph_id: uuid.UUID,
    payload: GraphPatch,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    graph = _require_graph(session, graph_id, user)
    data = payload.model_dump(exclude_unset=True)
    before = {k: getattr(graph, k) for k in data}
    for field, value in data.items():
        setattr(graph, field, value)

    audit_log.record(
        session=session,
        project_id=str(graph.project_id),
        actor=audit_log.Actor.human(str(user.id)),
        action="graph_updated",
        target_type=TargetKind.GRAPH,
        target_id=str(graph.id),
        before_value={k: str(v) for k, v in before.items()},
        after_value={k: str(v) for k, v in data.items()},
    )
    session.commit()
    session.refresh(graph)
    return _graph_out(graph)


@router.delete("/graphs/{graph_id}", status_code=204, tags=["graphs"])
def delete_graph(
    graph_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    graph = _require_graph(session, graph_id, user)
    session.delete(graph)
    session.commit()


def _require_graph(session: Session, graph_id: uuid.UUID, user: User) -> Graph:
    graph = session.get(Graph, graph_id)
    if graph is None:
        raise HTTPException(status_code=404, detail="graph not found")
    require_project(graph.project_id, session=session, user=user)
    return graph


def _graph_out(graph: Graph) -> GraphOut:
    """Build the response explicitly rather than ``GraphOut.model_validate(graph)``.

    Two reasons, both of which showed up as real 500s:

    * ``graph.series`` and ``graph.axes`` are relationship collections, so Pydantic
      attribute-accesses dicts and raises ``'dict' object has no attribute 'name'``.
    * Even where it survived, it emitted ``PydanticSerializationUnexpectedValue``
      warnings because the assigned values were dicts, not the declared models.

    Writing the mapping by hand also fixes the wire contract: axes come back in a stable
    x-then-y order rather than in whatever order the relationship loaded them, and the
    frontend can rely on that when it positions unit labels.
    """
    from scix.models import GraphAxis, GraphSeries

    return GraphOut(
        id=graph.id,
        project_id=graph.project_id,
        graph_type=graph.graph_type,
        name=graph.name,
        width_mm=graph.width_mm,
        height_mm=graph.height_mm,
        dpi=graph.dpi,
        source_analysis_id=graph.source_analysis_id,
        created_at=graph.created_at,
        series=[
            SeriesOut(
                id=s.id,
                name=s.name,
                x_column_id=s.x_column_id,
                y_column_id=s.y_column_id,
                error_basis=s.error_basis.value,
            )
            for s in sorted(graph.series, key=lambda x: x.ordinal)
        ],
        axes=[
            AxisOut(
                axis=a.axis,
                title=a.title,
                unit=a.unit,
                scale=a.scale.value,
                label_present=a.label_present,
            )
            for a in sorted(graph.axes, key=lambda x: (x.axis != "x", x.axis))
        ],
    )


def _analysis_out(analysis: StatisticalAnalysis) -> AnalysisOut:
    """Map the analysis explicitly rather than ``AnalysisOut.model_validate(analysis)``.

    ``analysis.parameters`` is a one-to-many of ``AnalysisParameter`` rows, and
    ``results``/``inputs`` are JSONB. Letting Pydantic walk that mixed graph through
    ``from_attributes`` raised ``'AnalysisParameter' object is not subscriptable``.

    Parameters are the reproducibility record -- every number needed to re-run the test by
    hand -- so they are returned in stored ``ordinal`` order, which is the order the test
    produced them and therefore the order a manuscript should cite them in.
    """
    return AnalysisOut(
        id=analysis.id,
        project_id=analysis.project_id,
        worksheet_id=analysis.worksheet_id,
        seq=analysis.seq,
        test_name=analysis.test_name,
        library=analysis.library,
        library_version=analysis.library_version,
        inputs=analysis.inputs,
        results=analysis.results,
        posthoc_test=analysis.posthoc_test,
        significance_level=analysis.significance_level,
        selected_by_id=analysis.selected_by_id,
        created_at=analysis.created_at,
        parameters=[
            ParameterOut(name=p.name, value=p.value, label=p.label)
            for p in sorted(analysis.parameters, key=lambda x: (x.ordinal, x.name))
        ],
    )


# --------------------------------------------------------------------------- #
# render spec  (ADR 0003)
# --------------------------------------------------------------------------- #
@router.get("/graphs/{graph_id}/render", response_model=RenderSpec, tags=["graphs"])
def render_spec(
    graph_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Concrete plottable series for the preview.

    The frontend draws this with Plotly. The export service feeds the same structure to
    Matplotlib, which is the authoritative renderer -- so a preview cannot drift from the
    exported figure.
    """
    graph = _require_graph(session, graph_id, user)
    spec = render_service.build_graph_spec(session, graph=graph)
    return RenderSpec.model_validate(spec)


# --------------------------------------------------------------------------- #
# significance  (R3 / S2 3.8)
# --------------------------------------------------------------------------- #
@router.post("/graphs/{graph_id}/significance", status_code=201, tags=["graphs"])
def add_significance(
    graph_id: uuid.UUID,
    payload: SignificanceMarkerRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Attach a significance marker backed by a real analysis.

    The database CHECK enforces the same rule. This route exists to return a useful error
    naming the missing analysis rather than a constraint violation naming a column.
    """
    graph = _require_graph(session, graph_id, user)

    analysis = session.get(StatisticalAnalysis, payload.analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "a significance marker must be derived from an analysis that actually ran "
                f"(analysis {payload.analysis_id} does not exist)"
            ),
        )
    if analysis.project_id != graph.project_id:
        raise HTTPException(status_code=403, detail="analysis belongs to another project")

    results = analysis.results or {}
    if "p_value" not in results:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{analysis.test_name.value} produced no p-value, so it cannot generate a "
                f"significance marker"
            ),
        )

    annotation = GraphAnnotation(
        graph_id=graph.id,
        kind=AnnotationKind.SIGNIFICANCE,
        marker=SignificanceMarker(payload.marker),
        content=_render_marker(payload.marker, results["p_value"]),
        source_analysis_id=analysis.id,
        attribution=Attributed.SOFTWARE,
        created_by_id=user.id,
        y_fraction=payload.y_fraction,
    )
    session.add(annotation)
    session.flush()

    audit_log.record(
        session=session,
        project_id=str(graph.project_id),
        actor=audit_log.Actor.software(audit_log.COMPONENT_GRAPH),
        action="significance_marker_added",
        target_type=TargetKind.GRAPH,
        target_id=str(graph.id),
        after_value={
            # ``.value`` is required: ``payload.marker`` is a SignificanceMarker enum and
            # JSONB cannot serialise an enum. Passing the enum object raised
            # "Object of type SignificanceMarker is not JSON serializable" from psycopg,
            # which named neither the marker nor the audit writer.
            "marker": payload.marker.value,
            "p_value": results["p_value"],
            "analysis_id": str(analysis.id),
            "test_name": analysis.test_name.value,
        },
    )
    session.commit()
    session.refresh(annotation)
    return {
        "id": str(annotation.id),
        "marker": payload.marker,
        "content": annotation.content,
        "source_analysis_id": str(analysis.id),
        "p_value": results["p_value"],
        "note": "derived from the analysis above; not an independent judgement",
    }


def _render_marker(marker: SignificanceMarker, p_value: float) -> str:
    """S2 3.8 marker vocabulary: both star notation and explicit p-values are supported,
    because journals differ.

    Takes the enum, not a string, and matches on the member -- comparing a plain
    ``Enum`` against a string is always False, which previously fell through and returned
    the enum object as the rendered text.
    """
    if marker is SignificanceMarker.P_EXACT:
        return f"p = {p_value:.4g}"
    if marker is SignificanceMarker.P_LT:
        return f"p < {p_value:.4g}" if p_value >= 0.001 else "p < 0.001"
    return marker.value


# --------------------------------------------------------------------------- #
# figure audit  (S2 3.12)
# --------------------------------------------------------------------------- #
@router.post("/graphs/{graph_id}/audit", response_model=FigureAuditOut, tags=["validation"])
def run_audit(
    graph_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run the twelve-point pre-export checklist and persist the run.

    Persisted so the audit has history: "this figure failed the unit check when it was
    submitted" must be an answer the platform can give.

    ``total_count`` and ``blocking`` are derived from the stored row rather than
    recomputed, so the response always describes the run that was actually persisted --
    including its timestamp, which is ``row.created_at`` and not "now".
    """
    graph = _require_graph(session, graph_id, user)
    row, checks = figure_service.audit_and_persist(
        session, graph, actor=audit_log.Actor.software(audit_log.COMPONENT_AUDIT)
    )
    session.commit()
    session.refresh(row)

    return FigureAuditOut(
        graph_id=row.graph_id,
        ran_at=row.created_at,
        passed_count=row.passed_count,
        total_count=len(row.checks),
        blocking=row.blocking_count > 0,
        items=[
            AuditItem(
                code=c.code,
                label=c.label,
                passed=c.passed,
                severity=c.severity,
                detail=c.detail,
                remedy=c.remedy,
            )
            for c in checks
        ],
    )


# --------------------------------------------------------------------------- #
# provenance / trace  (S2 3.13)
# --------------------------------------------------------------------------- #
@router.get("/graphs/{graph_id}/provenance", response_model=ProvenanceOut, tags=["provenance"])
def provenance(
    graph_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The S2 3.13 reproducibility panel, derived from live rows.

    Never read from a cache: reporting stale provenance as provenance would defeat the
    feature.
    """
    graph = _require_graph(session, graph_id, user)
    data = figure_service.build_provenance(session, graph)
    return ProvenanceOut(
        figure_label=data["figure_label"],
        source=_field(data["source"]),
        data=_field(data["data"]),
        processing=[
            TransformationStep(
                seq=s["seq"],
                transform_type=s["transform_type"],
                label=s["label"],
                params=s["params"],
                applied_at=s["applied_at"],
            )
            for s in data["processing"]
        ],
        analysis=_field(data["analysis"]),
        posthoc=_field(data["posthoc"]),
        plot=_field(data["plot"]),
        error=_field(data["error"]),
        created_by=_field(data["created_by"]),
        version=_field(data["version"]),
        completeness=data["completeness"],
    )


def _field(d: dict) -> ProvenanceField:
    return ProvenanceField(
        label=d["label"], value=d["value"], link_type=d["link_type"], link_id=d["link_id"]
    )


@router.get("/graphs/{graph_id}/trace", tags=["provenance"])
def trace(
    graph_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Every id the Trace action navigates to, plus chain health.

    Returns the destination ids rather than performing the navigation, so the frontend can
    offer the researcher a choice (open the worksheet, the analysis, or the base file)
    instead of silently moving them somewhere.
    """
    graph = _require_graph(session, graph_id, user)
    return figure_service.trace_targets(session, graph)


# --------------------------------------------------------------------------- #
# audit log
# --------------------------------------------------------------------------- #
@router.get("/audit/log", response_model=list[AuditLogOut], tags=["integrity"])
def audit_log_entries(
    project_id: uuid.UUID,
    target_type: str | None = None,
    target_id: str | None = None,
    limit: int = 100,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from scix.models import AuditLog

    project = require_project(project_id, session=session, user=user)
    stmt = select(AuditLog).where(AuditLog.project_id == project.id)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == TargetKind(target_type))
    if target_id:
        stmt = stmt.where(AuditLog.target_id == target_id)
    rows = session.execute(stmt.order_by(AuditLog.created_at.desc()).limit(min(limit, 500))).scalars().all()
    return [AuditLogOut.model_validate(r) for r in rows]
