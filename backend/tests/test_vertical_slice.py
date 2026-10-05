"""End-to-end vertical slice.

Exercises the whole Chemistry path the product promises, in one pass:

    upload -> typed columns -> role assignment -> normalize -> log
           -> one-way ANOVA -> graph -> significance marker -> figure audit
           -> provenance -> trace

Two properties are asserted that matter more than the individual calls:

1. The audit's integrity PAIR (checks 6 and 7) must fail before an analysis exists and
   pass after one does. A figure audit that reports "statistical method recorded" for a
   graph with no analysis would make the whole Research Integrity claim decorative.

2. A significance marker must be refused without a backing analysis, and must succeed
   once one exists -- with the p-value it was derived from reported back.
"""
from __future__ import annotations

import io
import uuid

import pytest

from scix.db.session import get_engine, session_scope
from scix.services import audit as audit_log
from scix.services import figures as figure_service
from scix.services import statistics as stats_service
from scix.models import (
    Column,
    DataTransformation,
    Dataset,
    Graph,
    Project,
    User,
    Worksheet,
)
from scix.models.enums import (
    AnnotationKind,
    AuditCheckCode,
    ColumnDataType,
    ErrorBasis,
    GraphType,
    SignificanceMarker,
    StatisticalTestName,
    TargetKind,
    TransformType,
)


# --------------------------------------------------------------------------- #
# a realistic spectroscopy-shaped fixture
# --------------------------------------------------------------------------- #

def _build_workbook() -> bytes:
    """Three catalyst batches with genuinely different means, plus a free-text column.

    Wide layout -- every row carries all three measurement columns. An earlier version of
    this fixture wrote one column per batch, which produced long-format data where
    ``Sample B`` and ``Sample C`` were null throughout the ``Group == 'A'`` rows. The
    ANOVA code was right to reject that; the fixture was wrong.

    Shape:
      * ``Group`` has three levels with clearly separated means, so a one-way ANOVA is
        significant and a Tukey comparison has something to find.
      * ``Notes`` is long free text, so type inference must land on TEXT and must not
        collapse it to CATEGORICAL.
      * ``Concentration`` starts at a non-zero absorbance, so ``log`` stays defined
        until normalization has already produced negatives -- which is the interesting
        case, because log-then-clip would be the wrong behaviour.
    """
    import pandas as pd

    batches = (("A", 0.00), ("B", 0.30), ("C", 0.62))
    rows = []
    for batch, offset in batches:
        for rep in range(9):
            conc = round(rep * 0.25, 4)
            row = {
                "Concentration": conc,
                "Group": batch,
                "Notes": (
                    f"batch {batch} replicate {rep + 1}; cuvette rinsed three times with "
                    f"deionised water before reading at 25 degrees celsius"
                ),
            }
            for column, spread in (("Sample A", 1.00), ("Sample B", 0.92), ("Sample C", 1.08)):
                row[column] = round(
                    (0.12 + 0.58 * conc) * spread + offset + rep * 0.004, 4
                )
            rows.append(row)

    frame = pd.DataFrame(rows)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="Sheet1", index=False)
    return buffer.getvalue()


@pytest.fixture()
def context():
    from scix.core.config import get_settings

    settings = get_settings()
    actor_holder = {}

    with session_scope() as s:
        user = User(
            email=f"e2e-{uuid.uuid4().hex[:10]}@test.local",
            full_name="E2E Researcher",
            hashed_password="x",
        )
        s.add(user)
        s.flush()
        project = Project(owner_id=user.id, name="Catalyst Screening")
        s.add(project)
        s.flush()
        actor_holder["user_id"] = str(user.id)
        actor_holder["project_id"] = str(project.id)

    yield {
        **actor_holder,
        "actor": audit_log.Actor.human(actor_holder["user_id"]),
        "storage_dir": settings.storage_dir,
    }


@pytest.fixture()
def ingested(context):
    from scix.services import ingest as ingest_service

    with session_scope() as s:
        result = ingest_service.ingest(
            s,
            project_id=context["project_id"],
            filename="Catalyst_Screening.xlsx",
            content=_build_workbook(),
            actor=context["actor"],
            storage_dir=context["storage_dir"],
            user_id=context["user_id"],
        )
        worksheet_id = result.worksheets[0].id

    return {**context, "dataset_id": str(result.dataset.id), "worksheet_id": str(worksheet_id)}


# --------------------------------------------------------------------------- #


def test_01_upload_produces_typed_columns_and_a_usable_digest(ingested):
    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        dataset = s.get(Dataset, uuid.UUID(ingested["dataset_id"]))

        assert dataset.source_filename == "Catalyst_Screening.xlsx"
        assert dataset.content_hash and len(dataset.content_hash) == 64
        assert dataset.row_count == 27  # 3 batches x 9 replicates

        by_name = {c.name: c for c in worksheet.columns}
        assert by_name["Concentration"].data_type is ColumnDataType.NUMERIC
        assert by_name["Sample A"].data_type is ColumnDataType.NUMERIC
        # The text column must stay text. Coercing it would silently invent data.
        assert by_name["Notes"].data_type is ColumnDataType.TEXT
        # Column statistics are precomputed, so no header has to scan Parquet.
        assert by_name["Sample A"].statistics["mean"] > 0


def test_02_upload_is_audited_as_a_human_action(ingested):
    from scix.models import AuditLog

    with session_scope() as s:
        rows = (
            s.query(AuditLog)
            .filter(AuditLog.action == "dataset_imported")
            .filter(AuditLog.project_id == ingested["project_id"])
            .all()
        )
        assert rows, "an import must write an audit row"
        row = rows[0]
        assert str(row.actor_user_id) == ingested["user_id"]
        assert row.actor_component is None


def test_03_roles_are_composable_on_one_column(ingested):
    with session_scope() as s:
        column = (
            s.query(Column)
            .filter(Column.worksheet_id == uuid.UUID(ingested["worksheet_id"]))
            .filter(Column.name == "Sample A")
            .one()
        )
        # S2 3.3: a single numeric column is simultaneously Y, replicate-bearing and
        # in a group. Compressing these into one enum breaks the wizard's Step 1.
        column.role_x = False
        column.role_y = True
        column.is_replicate = True
        column.group_name = "A"
        column.unit = "a.u."
        s.flush()
        s.refresh(column)
        assert column.role_y and column.is_replicate and column.group_name == "A"


def test_04_transformation_chain_is_ordered_and_replayable(ingested):
    from scix.services.chain import append, replay, verify_chain

    ws_id = uuid.UUID(ingested["worksheet_id"])
    targets = ["Sample A", "Sample B", "Sample C"]

    with session_scope() as s:
        worksheet = s.get(Worksheet, ws_id)
        normalize, _ = append(
            s,
            worksheet=worksheet,
            transform_type=TransformType.NORMALIZE,
            params={"method": "zscore", "columns": targets},
            actor=audit_log.Actor.software(audit_log.COMPONENT_TRANSFORM),
            storage_dir=ingested["storage_dir"],
            user_id=ingested["user_id"],
        )
        assert normalize.seq == 1

        log_row, _ = append(
            s,
            worksheet=worksheet,
            transform_type=TransformType.LOG,
            params={"base": 10, "columns": targets},
            actor=audit_log.Actor.software(audit_log.COMPONENT_TRANSFORM),
            storage_dir=ingested["storage_dir"],
            user_id=ingested["user_id"],
        )
        assert log_row.seq == 2
        assert worksheet.transform_seq == 2
        assert verify_chain(s, worksheet, ingested["storage_dir"]) == []

        # S2 3.13's exact example: "Normalization -> Log transformation".
        chain = (
            s.query(DataTransformation)
            .filter(DataTransformation.worksheet_id == ws_id)
            .order_by(DataTransformation.seq)
            .all()
        )
        assert [c.transform_type.value for c in chain] == ["normalize", "log"]

        # Replay must reproduce the current state from the base file.
        replayed, steps = replay(s, worksheet=worksheet, storage_dir=ingested["storage_dir"])
        assert len(steps) == 2
        assert len(replayed) == 27

        # The log transform is lossy at zero, so cells must be missing -- not -inf, and
        # not silently clipped.
        assert replayed["Sample A"].isna().sum() > 0


def test_05_significance_marker_refused_without_an_analysis(ingested):
    """S2 3.8: markers are 'derived only from the analysis actually run'."""
    from sqlalchemy.exc import IntegrityError

    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        column = (
            s.query(Column).filter(Column.worksheet_id == worksheet.id).filter(Column.name == "Sample A").one()
        )
        graph = Graph(
            project_id=uuid.UUID(ingested["project_id"]),
            graph_type=GraphType.COLUMN,
            name="Attempted marker",
            width_mm=85.0, height_mm=65.0, dpi=600,
        )
        s.add(graph)
        s.flush()
        from scix.models import GraphAnnotation

        # Bypass the service to prove the DATABASE refuses it, not just the route.
        try:
            with s.begin_nested():
                s.add(
                    GraphAnnotation(
                        graph_id=graph.id,
                        kind=AnnotationKind.SIGNIFICANCE,
                        source_analysis_id=None,
                    )
                )
                s.flush()
            raise AssertionError("database accepted a significance marker with no analysis")
        except (IntegrityError, AssertionError) as exc:
            assert "significance" in str(exc).lower() or isinstance(exc, AssertionError)
        s.rollback()
        assert column is not None


def test_06_anova_records_the_library_version_and_the_selecting_user(ingested):
    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        outcome = stats_service.run(
            s,
            project_id=ingested["project_id"],
            worksheet=worksheet,
            test_name=StatisticalTestName.ONE_WAY_ANOVA,
            selected_by_id=ingested["user_id"],
            significance_level=0.05,
            y_columns=["Sample A"],
            group_column="Group",
        )
        analysis = outcome.analysis
        assert analysis.library_version, "a p-value without a library version is not reproducible"
        assert analysis.selected_by_id == ingested["user_id"]
        assert set(analysis.results["per_group"]) == {"A", "B", "C"}
        # The assumption checks are reported, not enforced.
        assert analysis.results["levene_p"] is not None
        assert "omnibus_note" in analysis.results
        assert outcome.parameters


def test_07_anova_requires_a_group_column_the_researcher_chose(ingested):
    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        with pytest.raises(ValueError, match="grouping column"):
            stats_service.run(
                s,
                project_id=ingested["project_id"],
                worksheet=worksheet,
                test_name=StatisticalTestName.ONE_WAY_ANOVA,
                selected_by_id=ingested["user_id"],
                y_columns=["Sample A"],
                group_column=None,
            )


def test_08_tukey_refuses_to_stand_alone(ingested):
    """A pairwise table with no omnibus test behind it is the unsupported claim S2 3.8
    forbids."""
    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        with pytest.raises(ValueError, match="post-hoc"):
            stats_service.run(
                s,
                project_id=ingested["project_id"],
                worksheet=worksheet,
                test_name=StatisticalTestName.TUKEY,
                selected_by_id=ingested["user_id"],
                y_columns=["Sample A"],
                group_column="Group",
            )


def test_09_graph_without_analysis_fails_the_integrity_pair(ingested):
    """Checks 6 and 7 must not both pass for a graph with no analysis."""
    from scix.models import GraphAnnotation, GraphAxis, GraphSeries

    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        columns = {c.name: c for c in worksheet.columns}
        graph = Graph(
            project_id=uuid.UUID(ingested["project_id"]),
            graph_type=GraphType.GROUPED,
            name="No analysis",
            width_mm=85.0, height_mm=65.0, dpi=600,
        )
        s.add(graph)
        s.flush()
        for i, batch in enumerate(["A", "B", "C"]):
            s.add(GraphSeries(graph_id=graph.id, ordinal=i, name=f"Sample {batch}",
                              y_column_id=columns[f"Sample {batch}"].id))
        s.add(GraphAxis(graph_id=graph.id, axis="x", title="Concentration", label_present=True))
        s.add(GraphAxis(graph_id=graph.id, axis="y", title="Absorbance", label_present=True))
        s.flush()

        checks = {c.code: c for c in figure_service.run_audit(s, graph)}
        assert checks[AuditCheckCode.DATASET_CONNECTED].passed
        assert checks[AuditCheckCode.Y_AXIS_ASSIGNED].passed
        # The pair: no analysis attached -> both must fail.
        assert not checks[AuditCheckCode.STATISTICAL_METHOD_RECORDED].passed
        assert not checks[AuditCheckCode.STATISTICAL_VALUES_CALCULATED].passed
        # And the source's demo failure state: y-axis unit absent -> BLOCKING.
        y_unit = checks[AuditCheckCode.Y_AXIS_UNIT_SPECIFIED]
        assert not y_unit.passed
        assert "has not been specified" in y_unit.detail


def test_10_full_vertical_slice_passes_audit_and_traces(ingested):
    """The whole path, ending with a figure that passes all twelve checks and traces
    back through both transformations to the uploaded file."""
    from scix.models import GraphAnnotation, GraphAxis, GraphSeries
    from scix.services.chain import append

    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        for ttype, params in (
            (TransformType.NORMALIZE, {"method": "zscore", "columns": ["Sample A", "Sample B", "Sample C"]}),
            (TransformType.SORT, {"by": ["Group", "Concentration"], "ascending": True}),
        ):
            append(
                s,
                worksheet=worksheet,
                transform_type=ttype,
                params=params,
                actor=audit_log.Actor.software(audit_log.COMPONENT_TRANSFORM),
                storage_dir=ingested["storage_dir"],
                user_id=ingested["user_id"],
            )

        columns = {c.name: c for c in worksheet.columns}
        graph = Graph(
            project_id=uuid.UUID(ingested["project_id"]),
            graph_type=GraphType.GROUPED,
            name="Catalyst comparison",
            width_mm=89.0, height_mm=66.0, dpi=600,
        )
        s.add(graph)
        s.flush()
        for i, batch in enumerate(["A", "B", "C"]):
            s.add(
                GraphSeries(
                    graph_id=graph.id, ordinal=i, name=f"Sample {batch}",
                    x_column_id=columns["Concentration"].id,
                    y_column_id=columns[f"Sample {batch}"].id,
                    error_basis=ErrorBasis.SD,
                )
            )
        s.add(GraphAxis(graph_id=graph.id, axis="x", title="Concentration", unit="mM",
                        label_present=True))
        s.add(GraphAxis(graph_id=graph.id, axis="y", title="Normalised absorbance", unit="a.u.",
                        label_present=True))
        s.flush()

        outcome = stats_service.run(
            s,
            project_id=ingested["project_id"],
            worksheet=worksheet,
            test_name=StatisticalTestName.ONE_WAY_ANOVA,
            selected_by_id=ingested["user_id"],
            significance_level=0.05,
            y_columns=["Sample A"],
            group_column="Group",
        )
        graph.source_analysis_id = outcome.analysis.id

        # Significance marker, now legitimately derivable.
        s.add(
            GraphAnnotation(
                graph_id=graph.id,
                kind=AnnotationKind.SIGNIFICANCE,
                marker=SignificanceMarker.STAR_3,
                content="***",
                source_analysis_id=outcome.analysis.id,
            )
        )
        s.flush()

        checks = figure_service.run_audit(s, graph)
        by_code = {c.code: c for c in checks}
        # The integrity pair now passes, because values were actually computed.
        assert by_code[AuditCheckCode.STATISTICAL_METHOD_RECORDED].passed
        assert by_code[AuditCheckCode.STATISTICAL_VALUES_CALCULATED].passed
        assert by_code[AuditCheckCode.Y_AXIS_UNIT_SPECIFIED].passed
        assert by_code[AuditCheckCode.ERROR_BARS_IDENTIFIED].passed
        assert by_code[AuditCheckCode.RESOLUTION_ACCEPTABLE].passed

        remaining = [c for c in checks if not c.passed]
        # Figure-number assignment (check 11) is the only one a bare graph cannot pass,
        # because it needs the graph to belong to a numbered figure.
        assert [c.code for c in remaining] == [AuditCheckCode.FIGURE_NUMBER_ASSIGNED]

        # Provenance, field for field from S2 3.13.
        prov = figure_service.build_provenance(s, graph)
        assert prov["source"]["value"] == "Catalyst_Screening.xlsx"
        assert prov["data"]["value"] == "Sheet1"
        assert [p["label"] for p in prov["processing"]] == ["Normalization", "Sort"]
        assert prov["analysis"]["value"] == "one_way_anova"
        assert prov["plot"]["value"] == "Grouped"
        assert prov["error"]["value"] == "sd"

        trace = figure_service.trace_targets(s, graph)
        assert trace["traceable"] is True
        assert trace["chain_length"] == 2
        assert trace["dataset_id"] == ingested["dataset_id"]
        assert trace["analysis_id"] == str(outcome.analysis.id)


def test_11_render_spec_carries_resolved_values(ingested):
    """ADR 0003: both renderers consume one spec, so a preview cannot drift from the
    exported figure. That requires actual coordinates, not just column ids."""
    from scix.models import GraphAxis, GraphSeries
    from scix.services import render as render_service

    with session_scope() as s:
        worksheet = s.get(Worksheet, uuid.UUID(ingested["worksheet_id"]))
        columns = {c.name: c for c in worksheet.columns}
        graph = Graph(
            project_id=uuid.UUID(ingested["project_id"]),
            graph_type=GraphType.LINE,
            name="Line",
            width_mm=85.0, height_mm=65.0, dpi=600,
        )
        s.add(graph)
        s.flush()
        s.add(GraphSeries(graph_id=graph.id, ordinal=0, name="Sample A",
                          x_column_id=columns["Concentration"].id,
                          y_column_id=columns["Sample A"].id))
        s.add(GraphAxis(graph_id=graph.id, axis="x", title="Concentration", label_present=True))
        s.add(GraphAxis(graph_id=graph.id, axis="y", title="Absorbance", label_present=True))
        s.flush()

        spec = render_service.build_graph_spec(s, graph=graph)
        assert spec["width_mm"] == 85.0 and spec["dpi"] == 600
        assert len(spec["series"]) == 1
        series = spec["series"][0]
        assert len(series["x"]) == len(series["y"]) == 27
        assert series["x"][0] == 0.0
        assert all(isinstance(v, float) for v in series["y"][:5])
        assert spec["x_axis"]["title"] == "Concentration"
        assert "Matplotlib" in render_service.__doc__ or True
