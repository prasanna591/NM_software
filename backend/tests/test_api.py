"""The API contract, exercised over HTTP.

The service tests prove the logic. These prove the *contract* the frontend codes against:
status codes, response shapes, field names, and -- most importantly -- that the routes
refuse what the database refuses, with errors a UI can act on.

Run against the real Postgres. The constraints under test are native enums, JSONB and
CHECK constraints; an SQLite stand-in would pass while proving nothing.

Setup is carried by fixtures rather than by test ordering, so any single test can be run
in isolation with ``pytest tests/test_api.py::test_name``.
"""
from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from scix.api.app import create_app
from scix.db.session import session_scope, create_all
from scix.models import DisciplineProfile, FigureAudit, JournalPreset


@pytest.fixture(scope="module")
def client():
    create_all()
    with session_scope() as s:
        from scix.profiles.loader import sync_registry

        sync_registry(s)
    return TestClient(create_app())


def _workbook() -> bytes:
    import pandas as pd

    rows = []
    for batch, offset in (("A", 0.00), ("B", 0.30), ("C", 0.62)):
        for rep in range(9):
            conc = round(rep * 0.25, 4)
            row = {
                "Concentration": conc,
                "Group": batch,
                "Notes": f"batch {batch} replicate {rep + 1} measured at 25 degrees celsius",
            }
            for column, spread in (("Sample A", 1.00), ("Sample B", 0.92), ("Sample C", 1.08)):
                row[column] = round((0.12 + 0.58 * conc) * spread + offset + rep * 0.004, 4)
            rows.append(row)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(rows).to_excel(w, sheet_name="Sheet1", index=False)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# the walkthrough, built up by fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def project(client) -> dict:
    discipline = client.get("/api/disciplines/chemistry").json()
    r = client.post(
        "/api/projects",
        json={"name": "Catalyst Screening", "discipline_id": discipline["id"]},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["discipline_id"] == discipline["id"]
    return {"id": body["id"], "discipline": discipline}


@pytest.fixture(scope="module")
def uploaded(client, project) -> dict:
    r = client.post(
        "/api/data/upload",
        data={"project_id": project["id"]},
        files={
            "file": (
                "Catalyst_Screening.xlsx",
                _workbook(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert r.status_code == 201, r.text
    return {"body": r.json(), "project_id": project["id"]}


@pytest.fixture(scope="module")
def worksheet(client, uploaded) -> dict:
    """The worksheet, with composable roles set the way the wizard sets them."""
    project_id = uploaded["project_id"]
    dataset_id = client.get(f"/api/datasets?project_id={project_id}").json()[0]["id"]
    worksheet_id = client.get(f"/api/datasets/{dataset_id}").json()["worksheets"][0]["id"]

    detail = client.get(f"/api/worksheets/{worksheet_id}").json()
    column_id = next(c["id"] for c in detail["columns"] if c["name"] == "Sample A")
    r = client.patch(
        f"/api/columns/{column_id}",
        json={"role_y": True, "is_replicate": True, "group_name": "A", "unit": "a.u."},
    )
    assert r.status_code == 200, r.text
    return {"id": worksheet_id, "dataset_id": dataset_id, "detail": detail, "patched": r.json()}


@pytest.fixture(scope="module")
def chain(client, uploaded, worksheet) -> list:
    """Two ordered steps. This is the only way data changes."""
    project_id = uploaded["project_id"]
    worksheet_id = worksheet["id"]
    steps = []
    for payload in (
        {
            "transform_type": "normalize",
            "params": {
                "method": "zscore",
                "columns": ["Sample A", "Sample B", "Sample C"],
            },
        },
        {"transform_type": "sort", "params": {"by": ["Group", "Concentration"]}},
    ):
        r = client.post(
            "/api/data/transformations",
            params={"project_id": project_id, "worksheet_id": worksheet_id},
            json=payload,
        )
        assert r.status_code == 201, r.text
        steps.append(r.json())
    return steps


@pytest.fixture(scope="module")
def analysis(client, uploaded, worksheet) -> dict:
    r = client.post(
        "/api/statistics/analyze",
        params={"project_id": uploaded["project_id"]},
        json={
            "worksheet_id": worksheet["id"],
            "test_name": "one_way_anova",
            "y_columns": ["Sample A"],
            "group_column": "Group",
            "significance_level": 0.05,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def graph(client, uploaded, worksheet, analysis) -> dict:
    r = client.post(
        "/api/graphs/create",
        params={"project_id": uploaded["project_id"]},
        json={
            "worksheet_id": worksheet["id"],
            "graph_type": "grouped",
            "name": "Catalyst comparison",
            "source_analysis_id": analysis["id"],
            "series": [
                {
                    "name": f"Sample {b}",
                    "y_column": f"Sample {b}",
                    "x_column": "Concentration",
                    "error_basis": "sd",
                }
                for b in ("A", "B", "C")
            ],
            "axes": [
                {"axis": "x", "title": "Concentration", "unit": "mM", "scale": "linear"},
                {
                    "axis": "y",
                    "title": "Normalised absorbance",
                    "unit": "a.u.",
                    "scale": "linear",
                },
            ],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# discovery surfaces
# --------------------------------------------------------------------------- #


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["database"] == "up"


def test_invariants_endpoint_reports_what_postgres_enforces(client):
    """"The invariant is enforced by the database" should be checkable at runtime, not
    only in the test suite. A reviewer curls this and reads the actual constraints."""
    r = client.get("/api/integrity/invariants")
    assert r.status_code == 200
    body = r.json()

    checks = " ".join(c["definition"] for c in body["defensive_checks"])
    assert "attribution" in checks, "the attribution CHECK must be installed"
    assert "source_analysis_id" in checks, "significance requires an analysis"

    uniques = body["irreversible"]["transformation_order_unique"]
    assert any("seq" in u["definition"] for u in uniques), (
        "the ordered transformation log is enforced by a unique constraint"
    )


def test_wizard_options_carries_the_registries(client):
    """S2 3.7 fixes 21 tests; S2 3.2 fixes 19 graph types. The wizard must be offered
    exactly those, fetched server-side so it cannot drift from the enums."""
    r = client.get("/api/wizard/options")
    assert r.status_code == 200
    body = r.json()

    assert len(body["tests"]) == 21
    assert len(body["graph_types"]) == 19
    assert {d["key"] for d in body["disciplines"]} >= {"chemistry", "physics"}
    assert set(body["error_bases"]) == {"sd", "sem", "ci", "none"}
    assert "*" in body["significance_markers"]

    anova = next(t for t in body["tests"] if t["value"] == "one_way_anova")
    # S2 3.7 is a pedagogical requirement, not cosmetic: the wizard must explain the test.
    assert anova["description"]
    assert anova["assumptions"]
    assert anova["post_hoc"] == "tukey"
    assert anova["requires_group_column"] is True


def test_discipline_detail_comes_from_validated_yaml(client):
    r = client.get("/api/disciplines/chemistry")
    assert r.status_code == 200
    body = r.json()
    assert body["key"] == "chemistry"
    assert body["terminology_rule_count"] > 0
    assert body["manuscript_templates"]
    assert body["journal_requirements"]
    # Every seeded journal requirement carries a verifiable source (S2 3.10).
    for j in body["journal_requirements"]:
        assert j["rule_source"].startswith("http")
        assert j["rule_verified_at"]
    # The digest, so a profile edit on disk is visible.
    assert len(body["content_hash"]) == 64


def test_unknown_discipline_is_404_and_lists_alternatives(client):
    r = client.get("/api/disciplines/underwater-basket-weaving")
    assert r.status_code == 404
    assert "chemistry" in r.json()["detail"]


def test_journal_preset_exposes_staleness(client):
    """S2 3.10: a stale rule is still better than no rule, but it must be visible."""
    r = client.get("/api/journal-presets")
    assert r.status_code == 200
    presets = r.json()
    assert presets
    for p in presets:
        assert "is_stale" in p
        assert "days_since_verified" in p
        assert p["rule_source"]


# --------------------------------------------------------------------------- #
# projects and data
# --------------------------------------------------------------------------- #


def test_projects_are_scoped_to_their_owner(client, project):
    r = client.get("/api/projects")
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert project["id"] in ids


def test_upload_creates_typed_worksheet(uploaded):
    body = uploaded["body"]
    assert body["source_filename"] == "Catalyst_Screening.xlsx"
    assert len(body["content_hash"]) == 64
    assert body["row_count"] == 27
    assert len(body["worksheets"]) == 1


def test_worksheet_exposes_composable_roles(worksheet):
    names = {c["name"] for c in worksheet["detail"]["columns"]}
    assert {"Concentration", "Sample A", "Sample B", "Sample C", "Group", "Notes"} <= names

    by_name = {c["name"]: c for c in worksheet["detail"]["columns"]}
    assert by_name["Notes"]["data_type"] == "text"
    assert by_name["Sample A"]["data_type"] == "numeric"
    assert by_name["Sample A"]["group_name"] is None, "roles are not inferred"

    # Setting a role must not clear the others. S2 3.3: these are composable.
    updated = next(c for c in worksheet["patched"]["columns"] if c["name"] == "Sample A")
    assert updated["role_y"] is True
    assert updated["is_replicate"] is True
    assert updated["group_name"] == "A"
    assert updated["unit"] == "a.u."


def test_preview_returns_values_not_column_ids(client, worksheet):
    """ADR 0001: values live in Parquet, not Postgres. The grid still needs them."""
    r = client.get(f"/api/worksheets/{worksheet['id']}/preview?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] == 27
    assert body["truncated"] is True
    assert len(body["columns"][0]["values"]) == 5
    assert body["columns"][0]["values"][0] is not None


def test_transformation_chain_is_ordered(client, worksheet, chain):
    first, second = chain
    assert [t["seq"] for t in chain] == [1, 2]
    assert [t["transform_type"] for t in chain] == ["normalize", "sort"]
    assert first["rows_before"] == first["rows_after"] == 27

    r = client.get(f"/api/worksheets/{worksheet['id']}/transformations")
    assert r.status_code == 200
    listed = r.json()
    assert [t["seq"] for t in listed] == [1, 2]
    assert [t["transform_type"] for t in listed] == ["normalize", "sort"]


def test_replay_reproduces_the_chain(client, worksheet, chain):
    """The mechanism behind Trace Figure. Replays from the base file, not the current
    artefact, so a successful replay is evidence the chain reproduces the data."""
    r = client.get(f"/api/worksheets/{worksheet['id']}/replay")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["replayed_steps"] == 2
    assert body["row_count"] == 27
    assert [s["seq"] for s in body["chain"]] == [1, 2]
    assert body["chain"][0]["transform_type"] == "normalize"

    # upto_seq replays a prefix, which is what "undo the last step" needs.
    r = client.get(f"/api/worksheets/{worksheet['id']}/replay?upto_seq=1")
    assert r.json()["replayed_steps"] == 1


def test_replay_refuses_rather_than_guesses_when_the_chain_has_gaps(client, worksheet, chain):
    """An empty result is worse than a 409. If the log has a hole, replay cannot
    reproduce the data and must say so instead of returning a short frame.

    The hole is opened and closed inside one ``try`` so the shared module fixture is left
    intact for the tests that follow.
    """
    from scix.models import DataTransformation

    with session_scope() as s:
        victim = (
            s.query(DataTransformation)
            .filter(DataTransformation.worksheet_id == uuid.UUID(worksheet["id"]),
                    DataTransformation.seq == 1)
            .one()
        )
        saved = {
            "id": victim.id,
            "worksheet_id": victim.worksheet_id,
            "seq": victim.seq,
            "transform_type": victim.transform_type,
            "params": victim.params,
            "input_columns": victim.input_columns,
            "output_columns": victim.output_columns,
            "rows_before": victim.rows_before,
            "rows_after": victim.rows_after,
            "output_store_key": victim.output_store_key,
            "applied_by_id": victim.applied_by_id,
            "applied_at": victim.applied_at,
        }

    try:
        with session_scope() as s:
            s.delete(s.get(DataTransformation, saved["id"]))

        r = client.get(f"/api/worksheets/{worksheet['id']}/replay")
        assert r.status_code == 409
        detail = r.json()["detail"]
        assert "would not reproduce the data" in detail["message"]
        assert detail["problems"]
    finally:
        with session_scope() as s:
            s.add(DataTransformation(**saved))


def test_bad_transform_is_refused_with_a_readable_reason(client, uploaded, worksheet):
    r = client.post(
        "/api/data/transformations",
        params={"project_id": uploaded["project_id"], "worksheet_id": worksheet["id"]},
        json={"transform_type": "filter", "params": {"column": "No Such Column", "op": "notna"}},
    )
    assert r.status_code == 422
    assert "No Such Column" in r.json()["detail"]


# --------------------------------------------------------------------------- #
# statistics
# --------------------------------------------------------------------------- #


def test_anova_requires_an_explicit_group_column(client, uploaded, worksheet):
    """R3. There is no auto-detect. The researcher picks the grouping."""
    r = client.post(
        "/api/statistics/analyze",
        params={"project_id": uploaded["project_id"]},
        json={
            "worksheet_id": worksheet["id"],
            "test_name": "one_way_anova",
            "y_columns": ["Sample A"],
        },
    )
    assert r.status_code == 422
    assert "grouping column" in r.json()["detail"]


def test_anova_records_library_version_and_selecting_user(analysis):
    # Reproducibility: the library and version that produced the p-value.
    assert analysis["library"] == "scipy"
    assert analysis["library_version"]
    # R3: the researcher selected it.
    assert analysis["selected_by_id"]
    assert analysis["parameters"]
    assert analysis["parameters"]["group_column"] == "Group"


def test_anova_finds_the_separated_batches(analysis):
    results = analysis["results"]
    assert results["significant"] is True
    assert results["p_value"] < 0.05
    assert set(results["per_group"]) == {"A", "B", "C"}
    # The fixture has separated offsets, so the group means must be ordered.
    means = [results["per_group"][g]["mean"] for g in ("A", "B", "C")]
    assert means == sorted(means)


def test_tukey_cannot_be_run_standalone(client, uploaded, worksheet):
    """A pairwise table with no omnibus test behind it is the unsupported claim S2 3.8
    forbids."""
    r = client.post(
        "/api/statistics/analyze",
        params={"project_id": uploaded["project_id"]},
        json={
            "worksheet_id": worksheet["id"],
            "test_name": "tukey",
            "y_columns": ["Sample A"],
            "group_column": "Group",
        },
    )
    assert r.status_code == 422
    assert "post-hoc" in r.json()["detail"]


def test_posthoc_is_gated_on_the_omnibus_test(client, analysis):
    r = client.post(f"/api/statistics/analyses/{analysis['id']}/posthoc")
    assert r.status_code == 200, r.text
    assert r.json()["method"] == "Tukey HSD"


# --------------------------------------------------------------------------- #
# graphs
# --------------------------------------------------------------------------- #


def test_graph_rejects_a_column_from_another_worksheet(client, uploaded, worksheet):
    r = client.post(
        "/api/graphs/create",
        params={"project_id": uploaded["project_id"]},
        json={
            "worksheet_id": worksheet["id"],
            "graph_type": "line",
            "series": [{"name": "Ghost", "y_column": "Not A Column"}],
        },
    )
    assert r.status_code == 422
    assert "not in" in r.json()["detail"]


def test_graph_inherits_dpi_and_the_owning_analysis(graph, analysis):
    assert graph["dpi"] == 600
    assert len(graph["series"]) == 3
    assert graph["source_analysis_id"] == analysis["id"]


def test_render_spec_carries_values_for_both_renderers(client, graph):
    """ADR 0003: Plotly previews, Matplotlib exports, and both read this one spec."""
    r = client.get(f"/api/graphs/{graph['id']}/render")
    assert r.status_code == 200
    body = r.json()
    assert body["graph_type"] == "grouped"
    assert body["dpi"] == 600
    assert len(body["series"]) == 3

    series = body["series"][0]
    assert len(series["x"]) == len(series["y"]) == 27
    assert series["error_basis"] == "sd"
    assert body["x_axis"]["unit"] == "mM"
    assert "Matplotlib" in body["renderer_note"]


def test_significance_marker_refused_without_a_backing_analysis(client, uploaded, worksheet):
    r = client.post(
        "/api/graphs/create",
        params={"project_id": uploaded["project_id"]},
        json={
            "worksheet_id": worksheet["id"],
            "graph_type": "column",
            "name": "No analysis",
            "series": [{"name": "Sample A", "y_column": "Sample A"}],
            "axes": [
                {"axis": "x", "title": "Group"},
                {"axis": "y", "title": "Absorbance", "unit": "a.u."},
            ],
        },
    )
    orphan = r.json()["id"]

    r = client.post(
        f"/api/graphs/{orphan}/significance",
        json={"analysis_id": str(uuid.uuid4()), "marker": "***"},
    )
    assert r.status_code == 422
    assert "actually ran" in r.json()["detail"]


def test_significance_marker_is_derived_from_the_analysis(client, graph, analysis):
    r = client.post(
        f"/api/graphs/{graph['id']}/significance",
        json={"analysis_id": analysis["id"], "marker": "***", "y_fraction": 0.92},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_analysis_id"] == analysis["id"]
    assert body["p_value"] < 0.05
    assert body["marker"] == "***"
    assert "not an independent judgement" in body["note"]


def test_exact_p_value_marker_is_supported(client, graph, analysis):
    """S2 3.8: both star notation and explicit p-values, because journals differ."""
    r = client.post(
        f"/api/graphs/{graph['id']}/significance",
        json={"analysis_id": analysis["id"], "marker": "p_exact", "y_fraction": 0.98},
    )
    assert r.status_code == 201
    assert r.json()["content"].startswith("p = ")


def test_figure_audit_runs_twelve_checks(client, graph):
    r = client.post(f"/api/graphs/{graph['id']}/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["total_count"] == 12

    codes = [i["code"] for i in body["items"]]
    for expected in (
        "dataset_connected",
        "x_axis_assigned",
        "y_axis_assigned",
        "units_specified",
        "error_bars_identified",
        "statistical_method_recorded",
        "statistical_values_calculated",
        "resolution_acceptable",
        "axis_labels_present",
        "legend_present",
        "figure_number_assigned",
        "y_axis_unit_specified",
    ):
        assert expected in codes

    by_code = {i["code"]: i for i in body["items"]}
    # The integrity pair passes because values were actually computed.
    assert by_code["statistical_method_recorded"]["passed"] is True
    assert by_code["statistical_values_calculated"]["passed"] is True
    assert by_code["y_axis_unit_specified"]["passed"] is True
    assert by_code["resolution_acceptable"]["passed"] is True
    # Only figure numbering can fail on a bare graph.
    assert by_code["figure_number_assigned"]["passed"] is False
    assert body["blocking"] is False


def test_audit_persists_so_history_is_answerable(client, graph):
    """'This figure failed the unit check when it was submitted' must be answerable."""
    client.post(f"/api/graphs/{graph['id']}/audit")
    client.post(f"/api/graphs/{graph['id']}/audit")
    with session_scope() as s:
        runs = (
            s.query(FigureAudit).filter(FigureAudit.graph_id == uuid.UUID(graph["id"])).all()
        )
        assert len(runs) >= 2
        assert len(runs[0].checks) == 12


def test_provenance_panel_is_complete(client, graph):
    """S2 3.13, field for field."""
    r = client.get(f"/api/graphs/{graph['id']}/provenance")
    assert r.status_code == 200
    body = r.json()
    assert body["source"]["value"] == "Catalyst_Screening.xlsx"
    assert body["data"]["value"] == "Sheet1"
    assert [p["label"] for p in body["processing"]] == ["Normalization", "Sort"]
    assert body["analysis"]["value"] == "one_way_anova"
    assert body["plot"]["value"] == "Grouped"
    assert body["error"]["value"] == "sd"
    assert body["completeness"] == "complete"
    # Trace must be actionable, not a text summary.
    assert body["source"]["link_type"] == "dataset"
    assert body["source"]["link_id"]


def test_trace_returns_navigable_targets_and_chain_health(client, graph):
    r = client.get(f"/api/graphs/{graph['id']}/trace")
    assert r.status_code == 200
    body = r.json()
    assert body["traceable"] is True
    assert body["chain_problems"] == []
    assert body["chain_length"] == 2
    assert body["dataset_id"] and body["worksheet_id"] and body["analysis_id"]


def test_audit_log_records_the_whole_session(client, uploaded, graph):
    r = client.get(f"/api/audit/log?project_id={uploaded['project_id']}")
    assert r.status_code == 200
    entries = r.json()
    actions = {e["action"] for e in entries}
    assert {
        "dataset_imported",
        "transform_applied",
        "analysis_run",
        "graph_created",
        "significance_marker_added",
        "figure_audited",
    } <= actions

    # Every row is attributed. This is the invariant the whole product rests on.
    for e in entries:
        assert e["attribution"] in {"HUMAN", "SOFTWARE"}
        if e["attribution"] == "HUMAN":
            assert e["actor_user_id"]
        else:
            assert e["actor_component"], "a machine action must name its component"
