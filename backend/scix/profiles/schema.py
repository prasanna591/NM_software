"""Discipline profile schema.

docs/07 7.1: "Each discipline carries its own terminology, manuscript templates,
statistical methods, and journal formats -- on the same shared SCIX core."

The load-bearing architectural claim is that the *core* is shared and the *profiles* are
data. That claim is only true if a profile is expressible without touching Python. So
this module is the entire contract: any discipline that can be described by these
models can be added by dropping in a YAML file, and a profile that needs behaviour the
schema cannot express fails validation loudly instead of half-working.

Everything here is descriptive. Nothing in this file decides a scientific result.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- shared vocabulary --------------------------------------------------------- #
# A terminology rule is scoped to disciplines (docs/07 7.6: "the same string can be
# correct in one field and wrong in another"). "universal" is an explicit scope value
# rather than an empty list, because an empty list reads as "applies nowhere".
DisciplineScope = list[Literal["universal"] | str]

Severity = Literal["info", "warning", "error"]
NotationKind = Literal[
    "compound",
    "formula_subscript",
    "formula_superscript",
    "dash_style",
    "number_unit_spacing",
    "figure_reference",
    "table_reference",
    "spelling_locale",
    "gene",
    "protein",
    "math",
    "defined_term_case",
    "unit",
]

# How the fix is produced. This is the entire "code per discipline" surface, and it is
# two entries, not an ``if`` per discipline:
#
#   regex          -- the core builds the fix with re.sub(pattern, replacement). Handles
#                     closed compounds, dash style, spacing, reference forms.
#   formula_digits -- the core maps each matched ASCII digit to its Unicode subscript or
#                     superscript, ignoring ``replacement``. Digits are not string
#                     literals: 'CeNiO3' -> 'CeNiO3-with-a-subscript-3' cannot be written
#                     as one capture-group template, and a profile that pretends
#                     otherwise silently drops the two-digit case.
#
# Digit mapping is typography, not discipline knowledge. The profile decides *whether*
# the rule applies and *for which disciplines*; the shared core decides how a digit
# becomes a subscript. That split is what keeps `kind` from becoming a dispatch table
# with one branch per field.
TransformKind = Literal["regex", "formula_digits"]

SUBSCRIPT_MAP = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
SUPERSCRIPT_MAP = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")


class TerminologyRule(BaseModel):
    """One machine-checkable terminology rule.

    ``pattern`` is a Python regex, matched case-insensitively unless
    ``case_sensitive`` is set, because ``nano particle`` and ``Nano Particle`` are the
    same defect.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    kind: NotationKind
    description: str
    pattern: str
    replacement: str | None = None
    transform: TransformKind = "regex"
    severity: Severity = "warning"
    applies_to: DisciplineScope = Field(default_factory=lambda: ["universal"])
    case_sensitive: bool = False
    # Chemistry-specific: a rule like formula_subscript must not fire inside a code
    # span, a DOIs, or a citation.
    skip_code_spans: bool = True
    enabled: bool = True

    @model_validator(mode="after")
    def _replacement_required_for_regex_rewrites(self) -> "TerminologyRule":
        """A rule that finds problems but states no fix is still useful -- the
        researcher types the canonical form -- so ``replacement`` stays optional. But a
        ``regex`` rule with neither a replacement nor a description of what the canonical
        form is cannot be applied by anyone, so it is rejected."""
        if self.transform == "regex" and self.replacement is None and not self.description:
            raise ValueError(f"rule {self.id}: needs replacement or description")
        return self

    @model_validator(mode="after")
    def _formula_transform_is_consistent_with_kind(self) -> "TerminologyRule":
        """A digit-mapping transform on a non-formula rule (or vice versa) would mean the
        profile and the engine disagree about what the rule does. Fail here."""
        digit_kinds = {"formula_subscript", "formula_superscript"}
        if self.transform == "formula_digits" and self.kind not in digit_kinds:
            raise ValueError(
                f"rule {self.id}: transform 'formula_digits' requires kind "
                f"'formula_subscript' or 'formula_superscript', not {self.kind!r}"
            )
        if self.transform == "regex" and self.kind in digit_kinds and self.replacement:
            # A single capture-group template cannot map each digit individually, so a
            # replacement here means the two-digit case is silently unhandled.
            raise ValueError(
                f"rule {self.id}: kind {self.kind!r} needs transform 'formula_digits'; "
                "a regex replacement cannot subscript each digit of a multi-digit count"
            )
        return self

    @model_validator(mode="after")
    def _pattern_compiles(self) -> "TerminologyRule":
        import re

        try:
            re.compile(self.pattern)
        except re.error as exc:  # pragma: no cover - defensive
            raise ValueError(f"rule {self.id}: bad regex {self.pattern!r}: {exc}") from exc
        return self


class ManuscriptSectionTemplate(BaseModel):
    """A section of the manuscript skeleton (dimension 2: templates)."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    title: str
    required: bool = True
    guidance: str | None = None
    # Per-section word/character budgets. Advisory, surfaced in the editor.
    min_words: int | None = None
    max_words: int | None = None
    requires_figures: bool = False
    requires_references: bool = False


class ManuscriptTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    name: str
    description: str | None = None
    sections: list[ManuscriptSectionTemplate] = Field(min_length=1)

    @model_validator(mode="after")
    def _section_keys_unique(self) -> "ManuscriptTemplate":
        keys = [s.key for s in self.sections]
        if len(keys) != len(set(keys)):
            dupes = sorted({k for k in keys if keys.count(k) > 1})
            raise ValueError(f"duplicate section keys: {dupes}")
        return self

    @property
    def required_section_keys(self) -> list[str]:
        return [s.key for s in self.sections if s.required]


class StatisticalMethodDefault(BaseModel):
    """A default offered by the statistics wizard (dimension 3: stat methods).

    ``test`` must be a member of the ``statistical_test_name`` PostgreSQL enum, so a
    profile cannot advertise a test the database would refuse to store.
    """

    model_config = ConfigDict(extra="forbid")

    test: str
    label: str
    default_alpha: float = 0.05
    # When set, the wizard enables a post-hoc comparison if the omnibus test is
    # significant. docs/02: Tukey after ANOVA is the named pairing.
    post_hoc: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    guidance: str | None = None


class PlotCapability(BaseModel):
    """A plotting capability advertised for the discipline (docs/07 7.4).

    ``graph_type`` must be a member of the ``graph_type`` PostgreSQL enum.
    """

    model_config = ConfigDict(extra="forbid")

    graph_type: str
    label: str
    rationale: str | None = None
    default: bool = False


class JournalRequirementSeed(BaseModel):
    """Seed data for a ``journal_presets`` row.

    ``rule_source`` and ``rule_verified_at`` are required here for the same reason they
    are NOT NULL in the table (S2 3.10): a profile may not introduce a journal
    requirement whose origin cannot be shown to the researcher.
    """

    model_config = ConfigDict(extra="forbid")

    journal_name: str
    publisher: str | None = None
    rule_source: Annotated[str, Field(min_length=1)]
    rule_verified_at: str  # ISO date; validated below
    width_mm: float | None = None
    height_mm: float | None = None
    resolution_dpi: int | None = None
    file_format: str | None = None
    font_family: str | None = None
    min_font_pt: float | None = None
    max_panels: int | None = None
    citation_style: str | None = None
    stale_after_days: int = 365
    notes: str | None = None

    @model_validator(mode="after")
    def _date_is_iso(self) -> "JournalRequirementSeed":
        from datetime import date

        try:
            date.fromisoformat(self.rule_verified_at)
        except ValueError as exc:
            raise ValueError(
                f"journal {self.journal_name!r}: rule_verified_at must be ISO yyyy-mm-dd, "
                f"got {self.rule_verified_at!r}"
            ) from exc
        return self


class StyleDefaults(BaseModel):
    """docs/07 7.7 -- the choices the researcher must configure.

    Every one of these is a *choice presented to a human*, never a silent default that
    rewrites their manuscript. The checker proposes; the researcher applies.
    """

    model_config = ConfigDict(extra="forbid")

    figure_reference_form: str = "Figure"
    table_reference_form: str = "Table"
    dash_style: Literal["en-dash", "hyphen"] = "en-dash"
    spelling_locale: Literal["US", "UK"] = "US"
    formula_notation: Literal["unicode_subscripts", "latex", "plain"] = "unicode_subscripts"
    citation_style: str = "APA"
    voice_preference: Literal["prefer_active", "prefer_passive", "neutral"] = "prefer_active"
    # ``register`` shadows a pydantic BaseModel attribute, so it is aliased.
    register_: Literal["academic", "concise", "formal"] = Field(default="academic", alias="register")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class DisciplineProfileDoc(BaseModel):
    """A complete discipline profile, as loaded from ``profile.yaml``.

    The field set is exactly the four dimensions named in docs/07 7.1 plus the identity
    and style scaffolding around them. Adding a fifth dimension is a schema change; the
    point is that adding a *discipline* is not.
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=2, pattern=r"^[a-z0-9_]+$")
    display_name: str
    description: str = ""
    schema_version: int = 1
    extends: str | None = None

    terminology_rules: list[TerminologyRule] = Field(default_factory=list)
    manuscript_templates: list[ManuscriptTemplate] = Field(default_factory=list)
    statistical_methods: list[StatisticalMethodDefault] = Field(default_factory=list)
    plot_capabilities: list[PlotCapability] = Field(default_factory=list)
    journal_requirements: list[JournalRequirementSeed] = Field(default_factory=list)
    style_defaults: StyleDefaults = Field(default_factory=StyleDefaults)

    # --- cross-field validation ------------------------------------------------ #
    @model_validator(mode="after")
    def _rule_ids_unique(self) -> "DisciplineProfileDoc":
        ids = [r.id for r in self.terminology_rules]
        if len(ids) != len(set(ids)):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"duplicate terminology rule ids: {dupes}")
        return self

    @model_validator(mode="after")
    def _journal_names_unique(self) -> "DisciplineProfileDoc":
        names = [j.journal_name for j in self.journal_requirements]
        if len(names) != len(set(names)):
            dupes = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"duplicate journal requirements: {dupes}")
        return self

    @model_validator(mode="after")
    def _tests_and_graphs_exist_in_the_database_enums(self) -> "DisciplineProfileDoc":
        """A profile advertising an unknown test or graph type would fail at INSERT time
        with a Postgres error naming an internal enum. Catching it here names the
        profile and the offending value instead."""
        from scix.models.enums import GraphType, StatisticalTestName

        valid_tests = {t.value for t in StatisticalTestName}
        for m in self.statistical_methods:
            if m.test not in valid_tests:
                raise ValueError(
                    f"profile {self.key!r}: statistical method {m.test!r} is not in "
                    f"statistical_test_name enum. Valid: {sorted(valid_tests)}"
                )

        valid_graphs = {g.value for g in GraphType}
        for c in self.plot_capabilities:
            if c.graph_type not in valid_graphs:
                raise ValueError(
                    f"profile {self.key!r}: plot capability {c.graph_type!r} is not in "
                    f"graph_type enum. Valid: {sorted(valid_graphs)}"
                )
        return self

    @model_validator(mode="after")
    def _exactly_one_default_graph_per_type(self) -> "DisciplineProfileDoc":
        seen: dict[str, int] = {}
        for c in self.plot_capabilities:
            if c.default:
                seen[c.graph_type] = seen.get(c.graph_type, 0) + 1
        dupes = sorted(k for k, v in seen.items() if v > 1)
        if dupes:
            raise ValueError(f"more than one default plot capability for: {dupes}")
        return self

    # --- derived views used by services and the API ----------------------------- #
    def active_rules(self) -> list[TerminologyRule]:
        return [r for r in self.terminology_rules if r.enabled]

    def rules_for_kind(self, kind: NotationKind) -> list[TerminologyRule]:
        return [r for r in self.active_rules() if r.kind == kind]

    def default_graph_types(self) -> list[str]:
        return [c.graph_type for c in self.plot_capabilities if c.default]