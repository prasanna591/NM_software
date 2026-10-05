"""Project, discipline and journal-preset routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scix.api.deps import get_current_user, require_project
from scix.db.session import get_db
from scix.models import (
    Dataset,
    DisciplineProfile,
    Graph,
    JournalPreset,
    Project,
    StatisticalAnalysis,
    User,
)
from scix.models.enums import StatisticalTestName
from scix.profiles.loader import load_profile_cached
from scix.schemas.api import (
    DisciplineBrief,
    DisciplineDetail,
    GraphTypeOption,
    JournalPresetDetail,
    JournalPresetOut,
    PlotCapabilityBrief,
    ProjectCreate,
    ProjectOut,
    StatisticalMethodBrief,
    TestOption,
    UserOut,
    WizardOptions,
)

router = APIRouter()


# --------------------------------------------------------------------------- #
# me
# --------------------------------------------------------------------------- #
@router.get("/me", response_model=UserOut, tags=["identity"])
def me(user: User = Depends(get_current_user)) -> User:
    return user


# --------------------------------------------------------------------------- #
# projects
# --------------------------------------------------------------------------- #
@router.post("/projects", response_model=ProjectOut, status_code=201, tags=["projects"])
def create_project(
    payload: ProjectCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = Project(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        discipline_id=payload.discipline_id,
        target_journal_id=payload.target_journal_id,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut], tags=["projects"])
def list_projects(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    projects = session.execute(
        select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
    ).scalars().all()

    out = []
    for p in projects:
        dataset_count = session.execute(
            select(func.count()).select_from(Dataset).where(Dataset.project_id == p.id)
        ).scalar_one()
        graph_count = session.execute(
            select(func.count()).select_from(Graph).where(Graph.project_id == p.id)
        ).scalar_one()
        analysis_count = session.execute(
            select(func.count())
            .select_from(StatisticalAnalysis)
            .where(StatisticalAnalysis.project_id == p.id)
        ).scalar_one()
        out.append(
            ProjectOut(
                id=p.id, owner_id=p.owner_id, name=p.name, description=p.description,
                discipline_id=p.discipline_id, target_journal_id=p.target_journal_id,
                created_at=p.created_at,
                dataset_count=dataset_count, graph_count=graph_count,
                analysis_count=analysis_count,
            )
        )
    return out


@router.get("/projects/{project_id}", response_model=ProjectOut, tags=["projects"])
def get_project(
    project_id: uuid.UUID,
    project: Project = Depends(require_project),
):
    return project


@router.patch("/projects/{project_id}", response_model=ProjectOut, tags=["projects"])
def patch_project(
    project_id: uuid.UUID,
    payload: ProjectCreate,
    project: Project = Depends(require_project),
    session: Session = Depends(get_db),
):
    project.name = payload.name
    project.description = payload.description
    project.discipline_id = payload.discipline_id
    project.target_journal_id = payload.target_journal_id
    session.commit()
    session.refresh(project)
    return project


# --------------------------------------------------------------------------- #
# disciplines
# --------------------------------------------------------------------------- #
@router.get("/disciplines", response_model=list[DisciplineBrief], tags=["disciplines"])
def list_disciplines(session: Session = Depends(get_db)):
    rows = session.execute(
        select(DisciplineProfile).where(DisciplineProfile.is_active).order_by(DisciplineProfile.display_name)
    ).scalars().all()
    return [
        DisciplineBrief(id=r.id, key=r.key, display_name=r.display_name, description=r.description)
        for r in rows
    ]


@router.get("/disciplines/{key}", response_model=DisciplineDetail, tags=["disciplines"])
def get_discipline(key: str, session: Session = Depends(get_db)):
    """The full profile, straight from the validated YAML.

    Read from the file rather than the denormalised row: the file is the source of truth,
    and a profile edited on disk should take effect without a registry sync.
    """
    try:
        doc = load_profile_cached(key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid profile: {exc}") from exc

    from scix.profiles.loader import content_hash

    return DisciplineDetail(
        id=_profile_id(session, key),
        key=doc.key,
        display_name=doc.display_name,
        description=doc.description,
        terminology_rule_count=len(doc.terminology_rules),
        manuscript_templates=[t.model_dump(mode="json") for t in doc.manuscript_templates],
        statistical_methods=[
            StatisticalMethodBrief(
                test=m.test, label=m.label, default_alpha=m.default_alpha,
                post_hoc=m.post_hoc, assumptions=m.assumptions, guidance=m.guidance,
            )
            for m in doc.statistical_methods
        ],
        plot_capabilities=[
            PlotCapabilityBrief(
                graph_type=c.graph_type, label=c.label, rationale=c.rationale, default=c.default
            )
            for c in doc.plot_capabilities
        ],
        journal_requirements=[j.model_dump(mode="json") for j in doc.journal_requirements],
        style_defaults=doc.style_defaults.model_dump(),
        content_hash=content_hash(key),
    )


def _profile_id(session: Session, key: str) -> uuid.UUID:
    row = session.execute(
        select(DisciplineProfile).where(DisciplineProfile.key == key)
    ).scalar_one_or_none()
    if row is not None:
        return row.id
    # The YAML exists but has not been synced into the registry. Return a nil UUID so the
    # frontend can show the profile and offer to sync, rather than 404 on valid data.
    return uuid.UUID(int=0)


# --------------------------------------------------------------------------- #
# journal presets
# --------------------------------------------------------------------------- #
@router.get("/journal-presets", response_model=list[JournalPresetDetail], tags=["journals"])
def list_journal_presets(session: Session = Depends(get_db)):
    rows = session.execute(
        select(JournalPreset).where(JournalPreset.is_active).order_by(JournalPreset.journal_name)
    ).scalars().all()
    return [
        JournalPresetDetail(
            id=r.id, journal_name=r.journal_name, publisher=r.publisher,
            width_mm=r.width_mm, height_mm=r.height_mm, resolution_dpi=r.resolution_dpi,
            file_format=r.file_format, min_font_pt=r.min_font_pt, max_panels=r.max_panels,
            citation_style=r.citation_style, rule_source=r.rule_source,
            rule_verified_at=r.rule_verified_at, stale_after_days=r.stale_after_days,
            notes=r.notes, is_stale=r.is_stale, days_since_verified=r.days_since_verified,
        )
        for r in rows
    ]


@router.get("/journal-presets/{preset_id}", response_model=JournalPresetDetail, tags=["journals"])
def get_journal_preset(preset_id: uuid.UUID, session: Session = Depends(get_db)):
    r = session.get(JournalPreset, preset_id)
    if r is None:
        raise HTTPException(status_code=404, detail="journal preset not found")
    return JournalPresetDetail(
        id=r.id, journal_name=r.journal_name, publisher=r.publisher,
        width_mm=r.width_mm, height_mm=r.height_mm, resolution_dpi=r.resolution_dpi,
        file_format=r.file_format, min_font_pt=r.min_font_pt, max_panels=r.max_panels,
        citation_style=r.citation_style, rule_source=r.rule_source,
        rule_verified_at=r.rule_verified_at, stale_after_days=r.stale_after_days,
        notes=r.notes, is_stale=r.is_stale, days_since_verified=r.days_since_verified,
    )


# --------------------------------------------------------------------------- #
# wizard options  (S2 3.4 Step 2, S2 3.7 Step 3)
# --------------------------------------------------------------------------- #
@router.get("/wizard/options", response_model=WizardOptions, tags=["wizard"])
def wizard_options(session: Session = Depends(get_db)):
    """Everything the four-step wizard needs, in one request.

    Fetched once so the wizard cannot offer a graph type or test the backend would reject
    on submit. An option list assembled in the frontend drifts from the enum registry the
    moment either side changes.
    """
    from scix.models.enums import ErrorBasis, GraphType, SignificanceMarker
    from scix.services.figures import GRAPH_TYPE_GROUPS, GRAPH_TYPE_LABELS

    graph_types: list[GraphTypeOption] = []
    for group, members in GRAPH_TYPE_GROUPS:
        for gt in members:
            graph_types.append(
                GraphTypeOption(value=gt.value, label=GRAPH_TYPE_LABELS.get(gt, gt.value), group=group)
            )

    tests = [
        TestOption(
            value=t.value,
            label=_TEST_LABELS.get(t.value, t.value.replace("_", " ").title()),
            category=_TEST_CATEGORY.get(t.value, "Other"),
            description=_TEST_DESCRIPTIONS.get(t.value, ""),
            assumptions=_TEST_ASSUMPTIONS.get(t.value, []),
            post_hoc=_TEST_POST_HOC.get(t.value),
            requires_group_column=t.value in _TEST_NEEDS_GROUP,
        )
        for t in StatisticalTestName
    ]

    disciplines = [
        DisciplineBrief(id=r.id, key=r.key, display_name=r.display_name, description=r.description)
        for r in session.execute(
            select(DisciplineProfile).where(DisciplineProfile.is_active).order_by(DisciplineProfile.display_name)
        ).scalars().all()
    ]

    return WizardOptions(
        disciplines=disciplines,
        graph_types=graph_types,
        tests=tests,
        significance_markers=[m.value for m in SignificanceMarker],
        error_bases=[b.value for b in ErrorBasis],
    )


# S2 3.7: "SCIX explains what a test does; the researcher decides whether it's the right one."
_TEST_DESCRIPTIONS = {
    "descriptive_statistics": "Summarises a dataset: n, mean, SD, SEM, median, CV and 95% CI. Produces no comparison.",
    "t_test": "Compares the means of exactly two groups.",
    "paired_t_test": "Compares two measurements taken on the same subjects.",
    "one_way_anova": "Tests whether at least one of three or more group means differs. Does not say which.",
    "two_way_anova": "Tests two factors and their interaction.",
    "tukey": "Post-hoc pairwise comparison with family-wise error control. Requires a preceding one-way ANOVA.",
    "multiple_comparisons": "Post-hoc pairwise comparison for a general design.",
    "pearson": "Linear correlation between two continuous variables.",
    "spearman": "Monotonic correlation, robust to outliers and non-normal data.",
    "linear_regression": "Fits y = mx + b and reports slope, R² and the residuals.",
    "polynomial_regression": "Fits a polynomial of the requested degree.",
    "nonlinear_regression": "Fits a researcher-supplied model form.",
    "dose_response": "Fits a dose-response relationship and reports the fitted parameters.",
    "survival": "Time-to-event analysis.",
    "kaplan_meier": "Non-parametric survival curve estimation.",
    "roc": "Receiver operating characteristic and the area under it.",
    "time_series": "Models a measurement ordered in time.",
    "multivariate": "Joint analysis of several dependent variables.",
    "chi_square": "Categorical association in a contingency table.",
    "curve_fit": "Non-linear curve fitting across nine model families.",
    "custom": "A researcher-defined analysis.",
}

_TEST_ASSUMPTIONS = {
    "t_test": ["Independent observations in each group.", "Approximately normal within each group.", "Homogeneous variances (Welch relaxes this)."],
    "one_way_anova": ["Independent observations per group.", "Approximately normal within each group.", "Homogeneous variances across groups."],
    "pearson": ["Both variables continuous.", "Linearity.", "No influential outliers."],
    "spearman": ["Both variables at least ordinal.", "Monotonic rather than linear relationship."],
    "linear_regression": ["Linearity.", "Independent residuals.", "Homoscedasticity."],
}

_TEST_CATEGORY = {
    "descriptive_statistics": "Descriptive",
    "t_test": "Comparison",
    "paired_t_test": "Comparison",
    "one_way_anova": "Comparison",
    "two_way_anova": "Comparison",
    "tukey": "Post-hoc",
    "multiple_comparisons": "Post-hoc",
    "pearson": "Correlation",
    "spearman": "Correlation",
    "linear_regression": "Regression",
    "polynomial_regression": "Regression",
    "nonlinear_regression": "Regression",
    "dose_response": "Regression",
    "survival": "Clinical",
    "kaplan_meier": "Clinical",
    "roc": "Clinical",
    "time_series": "Time series",
    "multivariate": "Multivariate",
    "chi_square": "Categorical",
    "curve_fit": "Regression",
    "custom": "Other",
}

_TEST_LABELS = {
    "descriptive_statistics": "Descriptive statistics",
    "t_test": "t-test",
    "paired_t_test": "Paired t-test",
    "one_way_anova": "One-way ANOVA",
    "two_way_anova": "Two-way ANOVA",
    "tukey": "Tukey HSD",
    "multiple_comparisons": "Multiple comparisons",
    "pearson": "Pearson correlation",
    "spearman": "Spearman correlation",
    "linear_regression": "Linear regression",
    "polynomial_regression": "Polynomial regression",
    "nonlinear_regression": "Nonlinear regression",
    "dose_response": "Dose-response",
    "survival": "Survival analysis",
    "kaplan_meier": "Kaplan-Meier",
    "roc": "ROC analysis",
    "time_series": "Time-series",
    "multivariate": "Multivariate",
    "chi_square": "Chi-square / contingency",
    "curve_fit": "Curve fitting",
    "custom": "Custom analysis",
}

_TEST_POST_HOC = {
    "one_way_anova": "tukey",
    "two_way_anova": "multiple_comparisons",
}

_TEST_NEEDS_GROUP = {
    "one_way_anova", "two_way_anova", "t_test", "chi_square",
}
