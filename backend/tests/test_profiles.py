"""The discipline profile contract.

docs/07 7.1 makes the load-bearing architectural claim: "one core + N discipline
profiles", where a profile is *data*. That claim is only worth making if adding a
discipline needs no Python. These tests are what makes it checkable -- if a profile ever
requires an ``if`` statement, or a new enum value, one of these fails.

They also test the validation that stops a half-working profile from reaching a
researcher: a profile advertising a statistical test or graph type the database would
reject, or a journal requirement with no verifiable source, must fail loudly at load.
"""
from __future__ import annotations

import textwrap

import pytest

from scix.profiles.loader import available_profiles, load_all, load_profile, sync_registry
from scix.profiles.schema import DisciplineProfileDoc


def test_the_shipped_profiles_are_valid():
    """Every profile in the repository must load. A broken profile discovered by a
    researcher rather than by CI is the failure mode this prevents."""
    profiles = load_all()
    assert profiles, f"no profiles found under {available_profiles()}"
    for key, doc in profiles.items():
        assert doc.key == key
        assert doc.display_name


def test_adding_a_discipline_requires_no_code_change():
    """The core thesis. Chemistry and Physics differ in all four dimensions named by the
    source -- terminology, templates, statistics, journals -- and both load through the
    same schema with no Python change."""
    chemistry = load_profile("chemistry")
    physics = load_profile("physics")

    assert chemistry.key != physics.key

    # 1. terminology differs
    chem_rule_ids = {r.id for r in chemistry.terminology_rules}
    phys_rule_ids = {r.id for r in physics.terminology_rules}
    assert chem_rule_ids != phys_rule_ids
    assert chem_rule_ids - phys_rule_ids, "Chemistry should have rules Physics does not"

    # 2. manuscript templates differ
    assert {t.key for t in chemistry.manuscript_templates} != {
        t.key for t in physics.manuscript_templates
    }

    # 3. statistical methods differ
    assert {m.test for m in chemistry.statistical_methods} != {
        m.test for m in physics.statistical_methods
    }

    # 4. journal formats differ
    assert {j.journal_name for j in chemistry.journal_requirements} != {
        j.journal_name for j in physics.journal_requirements
    }


def test_every_journal_requirement_carries_a_verifiable_source():
    """S2 3.10: "the system shows the source and date of each journal requirement rather
    than silently assuming outdated rules." A requirement with no source cannot be shown,
    so the profile may not declare one."""
    for key, doc in load_all().items():
        for journal in doc.journal_requirements:
            assert journal.rule_source, f"{key}/{journal.journal_name} has no rule_source"
            assert journal.rule_source.startswith(("http://", "https://"))
            assert journal.rule_verified_at


def test_profile_may_not_advertise_a_test_the_database_would_reject():
    """The validator names the profile and the offending value. Without it this fails at
    INSERT time as a psycopg error about an internal enum, which tells a researcher
    nothing."""
    bad = textwrap.dedent(
        """
        key: bogus
        display_name: Bogus
        statistical_methods:
          - test: not_a_real_test
            label: Not real
        """
    )
    with pytest.raises(Exception, match="statistical_test_name"):
        DisciplineProfileDoc.model_validate(
            {
                "key": "bogus",
                "display_name": "Bogus",
                "statistical_methods": [{"test": "not_a_real_test", "label": "Not real"}],
            }
        )


def test_profile_may_not_advertise_an_unknown_graph_type():
    with pytest.raises(Exception, match="graph_type"):
        DisciplineProfileDoc.model_validate(
            {
                "key": "bogus",
                "display_name": "Bogus",
                "plot_capabilities": [
                    {"graph_type": "not_a_real_type", "label": "Not real"}
                ],
            }
        )


def test_formula_rule_may_not_claim_a_regex_replacement():
    """A regex replacement cannot map each digit of a multi-digit element count to its own
    subscript. A profile that tries is silently dropping the two-digit case, so it is
    rejected rather than half-applied."""
    with pytest.raises(Exception, match="formula_digits"):
        DisciplineProfileDoc.model_validate(
            {
                "key": "bogus",
                "display_name": "Bogus",
                "terminology_rules": [
                    {
                        "id": "bad_formula",
                        "kind": "formula_subscript",
                        "description": "subscripts",
                        "pattern": r"\b(Ca)10\b",
                        "replacement": r"\1₁₀",
                    }
                ],
            }
        )


def test_duplicate_rule_ids_are_rejected():
    """Two rules sharing an id would make a rejection keyed on (user, rule_id) ambiguous
    -- one dismissal would suppress a different rule."""
    rule = {
        "id": "dup",
        "kind": "compound",
        "description": "d",
        "pattern": r"\bx\b",
        "replacement": "y",
    }
    with pytest.raises(Exception, match="duplicate terminology rule ids"):
        DisciplineProfileDoc.model_validate(
            {
                "key": "bogus",
                "display_name": "Bogus",
                "terminology_rules": [rule, dict(rule)],
            }
        )


def test_unknown_field_is_rejected_not_ignored():
    """A misspelled key in a profile would otherwise be dropped in silence, and the rule
    it was meant to add would simply never fire."""
    with pytest.raises(Exception):
        DisciplineProfileDoc.model_validate(
            {
                "key": "bogus",
                "display_name": "Bogus",
                "terminology_rulez": [],
            }
        )


def test_registry_sync_is_idempotent():
    """sync_registry runs on deploy. It must not duplicate rows or churn the journal
    presets every time."""
    from scix.db.session import session_scope

    with session_scope() as s:
        first = sync_registry(s)
    with session_scope() as s:
        second = sync_registry(s)

    assert set(first) >= {"chemistry", "physics"}
    # Second run must find everything already present.
    assert second == [] or set(second).isdisjoint({"chemistry", "physics"})


def test_synced_registry_rows_carry_the_yaml_content():
    """The row is a pointer plus a digest, but the content is denormalised so a project
    can resolve its discipline in one query."""
    from scix.db.session import session_scope
    from scix.models import DisciplineProfile

    with session_scope() as s:
        sync_registry(s)

    with session_scope() as s:
        chemistry = s.query(DisciplineProfile).filter(DisciplineProfile.key == "chemistry").one()
        assert len(chemistry.content_hash) == 64
        assert chemistry.terminology_rules
        assert chemistry.manuscript_templates
        assert chemistry.statistical_methods
        assert chemistry.style_defaults["figure_reference_form"] == "Figure"
        assert chemistry.profile_summary["terminology_rule_count"] == len(
            chemistry.terminology_rules
        )


def test_profile_edit_changes_the_content_hash():
    """The digest exists so a profile edited on disk is visible as a change rather than
    silently absorbed by a running deployment."""
    import shutil
    import tempfile
    from pathlib import Path

    from scix.profiles.loader import content_hash, profile_path

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copytree(profile_path("chemistry").parent, root / "chemistry")
        before = content_hash("chemistry", profiles_dir=root)

        path = root / "chemistry" / "profile.yaml"
        path.write_text(path.read_text() + "\n# a comment\n")
        after = content_hash("chemistry", profiles_dir=root)

        assert before != after


def test_missing_profile_lists_the_known_ones():
    """A bad discipline key must name the alternatives, not just fail."""
    with pytest.raises(FileNotFoundError, match="chemistry"):
        load_profile("not_a_discipline")
