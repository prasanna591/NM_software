"""The invariants, as executable tests.

docs/08-roadmap.md 8.6 names two constraints as IRREVERSIBLE and three as defensive:

  IRREVERSIBLE
    1. audit_logs.attribution NOT NULL
    2. data_transformations is an ORDERED, replayable log
  DEFENSIVE
    3. significance annotations require a backing analysis      (R3)
    4. statistical_analyses.library_version NOT NULL            (reproducibility)
    5. journal_presets.rule_source + rule_verified_at NOT NULL   (S2 3.10)

These tests assert that the DATABASE rejects violations, not that the application
avoids them. An application-layer check can be bypassed by a raw insert, a migration,
a future service, or an engineer in a hurry. These cannot.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from scix.db.session import get_engine, session_scope
from scix.models import (
    Column,
    DataTransformation,
    Dataset,
    DisciplineProfile,
    Graph,
    GraphAnnotation,
    GraphAxis,
    GraphSeries,
    JournalPreset,
    Project,
    Section,
    StatisticalAnalysis,
    User,
    Worksheet,
)
from scix.models.enums import (
    AnnotationKind,
    Attributed,
    AxisScale,
    ColumnDataType,
    ErrorBasis,
    GraphType,
    StatisticalTestName,
    TransformType,
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _user() -> uuid.UUID:
    with session_scope() as s:
        u = User(email=f"inv-{uuid.uuid4().hex[:10]}@test.local", full_name="Test", hashed_password="x")
        s.add(u)
        s.flush()
        return u.id


def _project(user_id: uuid.UUID) -> uuid.UUID:
    with session_scope() as s:
        p = Project(owner_id=user_id, name="Invariant Project")
        s.add(p)
        s.flush()
        return p.id


def _dataset(project_id: uuid.UUID) -> uuid.UUID:
    with session_scope() as s:
        d = Dataset(
            project_id=project_id,
            source_filename="Experiment_01.xlsx",
            storage_key=f"datasets/{uuid.uuid4().hex}.xlsx",
        )
        s.add(d)
        s.flush()
        return d.id


def _worksheet(dataset_id: uuid.UUID) -> uuid.UUID:
    with session_scope() as s:
        w = Worksheet(dataset_id=dataset_id, name="Worksheet 1", column_store_key="ws/a.parquet")
        s.add(w)
        s.flush()
        return w.id


def _columns(worksheet_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    with session_scope() as s:
        x = Column(worksheet_id=worksheet_id, ordinal=0, name="Time", data_type=ColumnDataType.NUMERIC, role_x=True)
        a = Column(worksheet_id=worksheet_id, ordinal=1, name="Sample A", data_type=ColumnDataType.NUMERIC, role_y=True)
        b = Column(worksheet_id=worksheet_id, ordinal=2, name="Sample B", data_type=ColumnDataType.NUMERIC, role_y=True)
        s.add_all([x, a, b])
        s.flush()
        return x.id, a.id, b.id


def _analysis(project_id: uuid.UUID, worksheet_id: uuid.UUID, user_id: uuid.UUID) -> uuid.UUID:
    with session_scope() as s:
        a = StatisticalAnalysis(
            project_id=project_id,
            worksheet_id=worksheet_id,
            test_name=StatisticalTestName.ONE_WAY_ANOVA,
            library="statsmodels",
            library_version="0.14.4",
            inputs={"group_column": "group"},
            results={"p_value": 0.032},
            significance_level=0.05,
            selected_by_id=user_id,
        )
        s.add(a)
        s.flush()
        return a.id


def _graph(project_id: uuid.UUID, worksheet_id: uuid.UUID, cols) -> uuid.UUID:
    x_id, a_id, _ = cols
    with session_scope() as s:
        g = Graph(
            project_id=project_id,
            graph_type=GraphType.LINE,
            width_mm=85.0,
            height_mm=65.0,
            dpi=600,
        )
        s.add(g)
        s.flush()
        s.add(GraphSeries(graph_id=g.id, name="Sample A", x_column_id=x_id, y_column_id=a_id,
                          error_basis=ErrorBasis.SD))
        s.add(GraphAxis(graph_id=g.id, axis="x", title="Time", scale=AxisScale.LINEAR, label_present=True))
        s.add(GraphAxis(graph_id=g.id, axis="y", title="Activity", unit="a.u.", scale=AxisScale.LINEAR,
                        label_present=True))
        s.flush()
        return g.id


# --------------------------------------------------------------------------- #
# 1. IRREVERSIBLE -- attribution can never be absent
# --------------------------------------------------------------------------- #


def test_audit_log_rejects_null_attribution():
    """attribution NOT NULL. History with no author label is the failure this
    product exists to prevent, so the database must make it impossible."""
    user_id = _user()
    project_id = _project(user_id)
    engine = get_engine()

    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO audit_logs (project_id, attribution, action, target_type) "
                    "VALUES (:p, NULL, 'edit_accepted', 'SECTION')"
                ),
                {"p": project_id},
            )


def test_audit_log_rejects_software_attribution_to_a_person():
    """(actor_user_id IS NULL) = (attribution = 'SOFTWARE').

    A machine action must not be attributed to a named researcher."""
    user_id = _user()
    project_id = _project(user_id)

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.execute(
                text(
                    "INSERT INTO audit_logs (project_id, attribution, actor_user_id, action, target_type) "
                    "VALUES (:p, 'SOFTWARE', :u, 'edit_accepted', 'SECTION')"
                ),
                {"p": project_id, "u": user_id},
            )


def test_audit_log_rejects_human_attribution_without_a_person():
    """The converse: HUMAN always requires an actor. Prevents laundering a machine
    action through a user account."""
    user_id = _user()
    project_id = _project(user_id)

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.execute(
                text(
                    "INSERT INTO audit_logs (project_id, attribution, actor_user_id, action, target_type) "
                    "VALUES (:p, 'HUMAN', NULL, 'edit_accepted', 'SECTION')"
                ),
                {"p": project_id},
            )


def test_audit_log_accepts_both_legal_shapes():
    user_id = _user()
    project_id = _project(user_id)
    with session_scope() as s:
        s.execute(
            text(
                "INSERT INTO audit_logs (project_id, attribution, actor_user_id, action, target_type) "
                "VALUES (:p, 'HUMAN', :u, 'section_edited', 'SECTION')"
            ),
            {"p": project_id, "u": user_id},
        )
        s.execute(
            text(
                "INSERT INTO audit_logs (project_id, attribution, actor_user_id, actor_component, "
                "action, target_type) VALUES (:p, 'SOFTWARE', NULL, 'grammar', 'edit_accepted', 'SECTION')"
            ),
            {"p": project_id},
        )


# --------------------------------------------------------------------------- #
# 2. IRREVERSIBLE -- the transformation log is ordered
# --------------------------------------------------------------------------- #


def test_transformation_log_rejects_duplicate_sequence():
    """A duplicate seq would silently corrupt every downstream provenance record."""
    user_id = _user()
    project_id = _project(user_id)
    ds = _dataset(project_id)
    ws = _worksheet(ds)

    with session_scope() as s:
        s.add(DataTransformation(worksheet_id=ws, seq=1, transform_type=TransformType.NORMALIZE,
                                 params={"method": "zscore"}, applied_by_id=user_id))
        s.add(DataTransformation(worksheet_id=ws, seq=2, transform_type=TransformType.LOG,
                                 params={"base": 10}, applied_by_id=user_id))

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.add(DataTransformation(worksheet_id=ws, seq=1, transform_type=TransformType.FILTER,
                                     params={"col": "Sample A"}, applied_by_id=user_id))


def test_transformation_chain_is_queryable_in_order():
    """The spec's provenance example is a two-step chain. Reading it back in order
    must reproduce 'Normalization -> Log transformation' verbatim."""
    user_id = _user()
    project_id = _project(user_id)
    ws = _worksheet(_dataset(project_id))

    with session_scope() as s:
        for seq, ttype in enumerate([TransformType.NORMALIZE, TransformType.LOG], start=1):
            s.add(DataTransformation(worksheet_id=ws, seq=seq, transform_type=ttype,
                                     params={}, applied_by_id=user_id))

    with session_scope() as s:
        chain = (
            s.query(DataTransformation)
            .filter(DataTransformation.worksheet_id == ws)
            .order_by(DataTransformation.seq)
            .all()
        )
        assert [c.seq for c in chain] == [1, 2]
        assert [c.transform_type.value for c in chain] == ["normalize", "log"]


# --------------------------------------------------------------------------- #
# 3. DEFENSIVE -- significance markers require a backing analysis (R3)
# --------------------------------------------------------------------------- #


def test_significance_annotation_requires_an_analysis():
    """S2 3.8: markers are 'derived only from the analysis actually run'. There must
    be no INSERT that can produce an unsupported marker."""
    user_id = _user()
    project_id = _project(user_id)
    ws = _worksheet(_dataset(project_id))
    cols = _columns(ws)
    graph_id = _graph(project_id, ws, cols)

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.add(GraphAnnotation(graph_id=graph_id, kind=AnnotationKind.SIGNIFICANCE,
                                 source_analysis_id=None, attribution=Attributed.SOFTWARE))


def test_non_significance_annotation_needs_no_analysis():
    user_id = _user()
    project_id = _project(user_id)
    ws = _worksheet(_dataset(project_id))
    cols = _columns(ws)
    graph_id = _graph(project_id, ws, cols)

    with session_scope() as s:
        s.add(GraphAnnotation(graph_id=graph_id, kind=AnnotationKind.TEXT, content="note"))
        assert s.query(GraphAnnotation).filter(GraphAnnotation.graph_id == graph_id).count() == 1


def test_significance_annotation_with_analysis_is_accepted():
    user_id = _user()
    project_id = _project(user_id)
    ws = _worksheet(_dataset(project_id))
    cols = _columns(ws)
    analysis_id = _analysis(project_id, ws, user_id)
    graph_id = _graph(project_id, ws, cols)

    with session_scope() as s:
        s.add(GraphAnnotation(graph_id=graph_id, kind=AnnotationKind.SIGNIFICANCE,
                             source_analysis_id=analysis_id, attribution=Attributed.SOFTWARE))
        assert s.query(GraphAnnotation).filter(GraphAnnotation.graph_id == graph_id).count() == 1


# --------------------------------------------------------------------------- #
# 4. DEFENSIVE -- reproducibility
# --------------------------------------------------------------------------- #


def test_analysis_requires_library_version():
    """A p-value without the library version that produced it is not reproducible."""
    user_id = _user()
    project_id = _project(user_id)
    ws = _worksheet(_dataset(project_id))

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.execute(
                text(
                    "INSERT INTO statistical_analyses (project_id, worksheet_id, test_name, library, "
                    "inputs, results, selected_by_id) "
                    "VALUES (:p, :w, 'ONE_WAY_ANOVA', 'statsmodels', '{}', '{}', :u)"
                ),
                {"p": project_id, "w": ws, "u": user_id},
            )


def test_analysis_requires_a_selecting_user():
    """R3: the researcher chooses the analysis. There is no auto-select path."""
    user_id = _user()
    project_id = _project(user_id)
    ws = _worksheet(_dataset(project_id))

    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.execute(
                text(
                    "INSERT INTO statistical_analyses (project_id, worksheet_id, test_name, library, "
                    "library_version, inputs, results, selected_by_id) "
                    "VALUES (:p, :w, 'ONE_WAY_ANOVA', 'statsmodels', '0.14.4', '{}', '{}', NULL)"
                ),
                {"p": project_id, "w": ws},
            )


# --------------------------------------------------------------------------- #
# 5. DEFENSIVE -- journal preset provenance (S2 3.10)
# --------------------------------------------------------------------------- #


def test_journal_preset_requires_rule_source_and_verification_date():
    """'The system shows the source and date of each journal requirement rather than
    silently assuming outdated rules.' A preset with no source cannot show one."""
    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.execute(
                text(
                    "INSERT INTO journal_presets (journal_name, rule_source, rule_verified_at) "
                    "VALUES ('Journal of Tests', NULL, NULL)"
                )
            )


def test_journal_preset_reports_staleness():
    """A real but old rule is still better than no rule -- but it must be visible."""
    from datetime import date, timedelta

    with session_scope() as s:
        jp = JournalPreset(
            journal_name=f"Stale Journal {uuid.uuid4().hex[:6]}",
            rule_source="https://example.org/author-guidelines",
            rule_verified_at=date.today() - timedelta(days=500),
            stale_after_days=365,
        )
        s.add(jp)
        s.flush()
        assert jp.is_stale is True
        assert jp.days_since_verified >= 500

    with session_scope() as s:
        jp = JournalPreset(
            journal_name=f"Fresh Journal {uuid.uuid4().hex[:6]}",
            rule_source="https://example.org/author-guidelines",
            rule_verified_at=date.today(),
            stale_after_days=365,
        )
        s.add(jp)
        s.flush()
        assert jp.is_stale is False


# --------------------------------------------------------------------------- #
# 6. Column roles are composable (S2 3.3)
# --------------------------------------------------------------------------- #


def test_column_roles_are_independent_not_one_enum():
    """A numeric column can be a Y, a replicate-bearing column, and in a group,
    simultaneously. Compressing these into one column type breaks the wizard."""
    user_id = _user()
    project_id = _project(user_id)
    ws = _worksheet(_dataset(project_id))

    with session_scope() as s:
        c = Column(
            worksheet_id=ws,
            ordinal=0,
            name="Sample A",
            data_type=ColumnDataType.NUMERIC,
            role_x=False,
            role_y=True,
            is_replicate=True,
            group_name="Sample A",
        )
        s.add(c)
        s.flush()
        assert c.role_y and c.is_replicate and c.group_name == "Sample A"
        assert not c.role_x


# --------------------------------------------------------------------------- #
# 7. Discipline profile is data
# --------------------------------------------------------------------------- #


def test_discipline_profile_is_a_registry_row():
    """docs/07 7.1: all four discipline-varying things are DATA. Adding a discipline
    must never require an application change."""
    with session_scope() as s:
        p = DisciplineProfile(
            key=f"test-discipline-{uuid.uuid4().hex[:6]}",
            display_name="Test Discipline",
            profile_path="profiles/test/profile.yaml",
            content_hash="0" * 64,
        )
        s.add(p)
        s.flush()
        assert p.profile_path.endswith("profile.yaml")


def test_discipline_profile_row_cannot_exist_without_a_content_hash():
    """The registry row is a pointer to the YAML plus a digest of it. Without the digest,
    an edit to a profile on disk is invisible to a running deployment -- it would look
    unchanged while every rule in it had moved."""
    with pytest.raises(IntegrityError):
        with session_scope() as s:
            s.execute(
                text(
                    "INSERT INTO discipline_profiles (key, display_name, profile_path, content_hash) "
                    "VALUES ('no-hash', 'No Hash', 'profiles/no-hash/profile.yaml', NULL)"
                )
            )
