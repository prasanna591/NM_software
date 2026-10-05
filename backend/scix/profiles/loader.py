"""Profile loading and the registry that makes profiles data.

Two halves:

* :func:`load_profile` reads and validates one ``profile.yaml``. A profile that does not
  satisfy the schema raises, naming the file and the field. It is never partially loaded.

* :func:`sync_registry` writes profiles into the ``discipline_profiles`` table so that
  projects can reference a discipline by foreign key. The YAML file remains the source
  of truth for the profile *contents*; the row is a pointer plus a content hash, so a
  profile edit is visible as a hash change rather than silently absorbed.
"""
from __future__ import annotations

import hashlib
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from scix.core.config import get_settings
from scix.profiles.schema import DisciplineProfileDoc

PROFILE_FILENAME = "profile.yaml"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def profile_path(key: str, profiles_dir: Path | None = None) -> Path:
    root = profiles_dir or get_settings().profiles_dir
    return root / key / PROFILE_FILENAME


def load_profile(key: str, profiles_dir: Path | None = None) -> DisciplineProfileDoc:
    """Load and validate one profile by key."""
    path = profile_path(key, profiles_dir)
    if not path.exists():
        known = sorted(available_profiles(profiles_dir))
        raise FileNotFoundError(f"no discipline profile {key!r} at {path}. Known: {known}")

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level")

    declared = data.get("key")
    if declared != key:
        # A directory name that disagrees with its own key is the kind of mismatch that
        # produces a profile registered under one discipline and displayed as another.
        raise ValueError(f"{path}: declares key {declared!r} but lives in directory {key!r}")

    doc = DisciplineProfileDoc.model_validate(data)
    if doc.extends:
        _apply_inheritance(doc, profiles_dir or get_settings().profiles_dir)
    return doc


def _apply_inheritance(doc: DisciplineProfileDoc, profiles_dir: Path) -> None:
    """Merge a parent profile underneath this one.

    Parent values fill gaps only. The child always wins, so a profile can tighten a rule
    without restating the parent's whole list.
    """
    parent = load_profile(doc.extends, profiles_dir)

    have_rule_ids = {r.id for r in doc.terminology_rules}
    merged_rules = [r.model_copy(deep=True) for r in parent.terminology_rules]
    merged_rules += [r.model_copy(deep=True) for r in doc.terminology_rules]
    # Later definitions win on id collision, so an overriding rule replaces the parent's.
    by_id: dict[str, object] = {}
    for r in merged_rules:
        by_id[r.id] = r
    doc.terminology_rules = list(by_id.values())  # type: ignore[attr-defined]

    have_template_keys = {t.key for t in doc.manuscript_templates}
    templates = [t.model_copy(deep=True) for t in parent.manuscript_templates]
    templates += [t.model_copy(deep=True) for t in doc.manuscript_templates]
    seen_t: dict[str, object] = {}
    for t in templates:
        seen_t[t.key] = t
    doc.manuscript_templates = list(seen_t.values())  # type: ignore[attr-defined]

    have_tests = {m.test for m in doc.statistical_methods}
    methods = [m.model_copy(deep=True) for m in parent.statistical_methods]
    methods += [m for m in doc.statistical_methods if m.test not in have_tests]
    doc.statistical_methods = methods  # type: ignore[attr-defined]

    have_caps = {c.graph_type for c in doc.plot_capabilities}
    caps = [c.model_copy(deep=True) for c in parent.plot_capabilities]
    caps += [c for c in doc.plot_capabilities if c.graph_type not in have_caps]
    doc.plot_capabilities = caps  # type: ignore[attr-defined]

    have_journals = {j.journal_name for j in doc.journal_requirements}
    journals = [j.model_copy(deep=True) for j in parent.journal_requirements]
    journals += [j for j in doc.journal_requirements if j.journal_name not in have_journals]
    doc.journal_requirements = journals  # type: ignore[attr-defined]

    del have_rule_ids


def available_profiles(profiles_dir: Path | None = None) -> list[str]:
    """Keys of every profile directory containing a ``profile.yaml``."""
    root = profiles_dir or get_settings().profiles_dir
    if not root.exists():
        return []
    return sorted(
        d.name for d in root.iterdir() if d.is_dir() and (d / PROFILE_FILENAME).exists()
    )


@lru_cache(maxsize=32)
def load_profile_cached(key: str) -> DisciplineProfileDoc:
    """Cached load for request paths. Returns a deep copy so a caller cannot mutate the
    cached document for the next request."""
    return load_profile(key).model_copy(deep=True)


def load_all(profiles_dir: Path | None = None) -> dict[str, DisciplineProfileDoc]:
    """Every profile on disk. Used by ``sync_registry`` and the API's discipline listing.

    One bad profile does not hide the good ones: failures are collected and reported
    together, because a half-loaded registry is how a discipline silently disappears.
    """
    out: dict[str, DisciplineProfileDoc] = {}
    errors: list[str] = []
    for key in available_profiles(profiles_dir):
        try:
            out[key] = load_profile(key, profiles_dir)
        except Exception as exc:
            errors.append(f"{key}: {exc}")
    if errors:
        raise ValueError("invalid discipline profiles:\n  " + "\n  ".join(errors))
    return out


def content_hash(key: str, profiles_dir: Path | None = None) -> str:
    path = profile_path(key, profiles_dir)
    return _hash_text(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# registry sync
# --------------------------------------------------------------------------- #


def sync_registry(session) -> list[str]:
    """Upsert profiles into ``discipline_profiles`` and ``journal_presets``.

    Idempotent: running it against an unchanged profile tree writes nothing new and
    changes no row. Safe to call on every deploy.

    Returns the keys written.
    """
    from scix.models import DisciplineProfile, JournalPreset

    profiles = load_all()
    written: list[str] = []

    for key, doc in profiles.items():
        digest = content_hash(key)
        row = session.query(DisciplineProfile).filter(DisciplineProfile.key == key).one_or_none()

        summary = {
            "terminology_rule_count": len(doc.terminology_rules),
            "manuscript_template_count": len(doc.manuscript_templates),
            "statistical_method_count": len(doc.statistical_methods),
            "plot_capability_count": len(doc.plot_capabilities),
            "journal_requirement_count": len(doc.journal_requirements),
            "extends": doc.extends,
            "style_defaults": doc.style_defaults.model_dump(),
        }

        if row is None:
            row = DisciplineProfile(
                key=key,
                display_name=doc.display_name,
                profile_path=f"{key}/{PROFILE_FILENAME}",
            )
            session.add(row)
            written.append(key)
        else:
            row.display_name = doc.display_name
            row.profile_path = f"{key}/{PROFILE_FILENAME}"

        row.content_hash = digest
        row.terminology_rules = [r.model_dump(mode="json") for r in doc.terminology_rules]
        row.manuscript_templates = [t.model_dump(mode="json") for t in doc.manuscript_templates]
        row.statistical_methods = [m.model_dump(mode="json") for m in doc.statistical_methods]
        row.plot_capabilities = [c.model_dump(mode="json") for c in doc.plot_capabilities]
        row.style_defaults = summary["style_defaults"]
        row.profile_summary = summary

        _sync_journals(session, doc, written)

    session.flush()
    return written


def _sync_journals(session, doc, written: list[str]) -> None:
    from scix.models import JournalPreset

    for seed in doc.journal_requirements:
        verified = date.fromisoformat(seed.rule_verified_at)
        row = (
            session.query(JournalPreset)
            .filter(JournalPreset.journal_name == seed.journal_name)
            .one_or_none()
        )
        if row is None:
            row = JournalPreset(journal_name=seed.journal_name)
            session.add(row)
            written.append(f"journal:{seed.journal_name}")

        row.publisher = seed.publisher
        row.rule_source = seed.rule_source
        row.rule_verified_at = verified
        row.width_mm = seed.width_mm
        row.height_mm = seed.height_mm
        row.resolution_dpi = seed.resolution_dpi
        row.file_format = seed.file_format
        row.font_family = seed.font_family
        row.min_font_pt = seed.min_font_pt
        row.max_panels = seed.max_panels
        row.citation_style = seed.citation_style
        row.stale_after_days = seed.stale_after_days
        row.notes = seed.notes