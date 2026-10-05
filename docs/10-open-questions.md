# 10 — Open Questions, Gaps & Contradictions

Every ambiguity, inconsistency, omission and undecided decision found while extracting the two
source documents. Ordered by development impact. **Resolve Q1–Q10 before writing the first
migration.**

---

## Q1 — Navigation: five menus or nine? (contradiction, both sources)

**S2 §02 prose (L433):** "Five top-level menus carry the whole workflow."
**S2 §02 cards (L436–471):** five cards — DATA, ANALYSIS, PLOT, FORMAT, EXPORT.
**S2 §01 wireframe (L410):** nine menu-bar items — File, Data, Analysis, Plot, **Statistics**,
Format, **Journal**, **Validate**, **Help**.

Statistics, Journal and Validate are top-level in the wireframe but not in the card list. File and
Help have no card.

**Decision needed:** is the shipped menu bar the 5-card set, the 9-item set, or a superset?
**Recommendation:** adopt the 9-item wireframe. `Statistics` and `Journal` are substantial feature
areas (21 tests; journal presets + submission prep) and burying `Validate` inside `Export` would
hide the product's differentiator. Treat `File` and `Help` as chrome, not workflow menus.
**Impact:** navigation architecture, routing, permission model.

## Q2 — Product name and white-labelling (ambiguity, both sources)

S1 brands the product **NM Scientific Research Studio**. S1 also uses **SCIX** for the authorship
policy and the "shared SCIX core". S2 is **SCIX Plot Studio** throughout. No rule is given for which
name appears where.

**Decision needed:** single canonical name, or dual-brand with a rule? Is white-labelling for
Stage 4 institutions required (implied by "University accounts")?
**Recommendation:** `SCIX` as the internal product and repo namespace; `NM Scientific Research
Studio` as the default display brand; both stored in config so an institution can override.
**Impact:** branding across the UI, package names, email templates.

## Q3 — Discipline roster mismatch (contradiction, both sources)

S1 lists 19 disciplines (L422–429). S2 §14 lists 7 with different groupings.

| Problem | Detail |
|---------|---------|
| **Materials Science** | Named in S2, absent from S1's 19 |
| **Uncovered by S2** | Physics, Biotechnology, Pharmacy, AI/Data Science, Mathematics, Environmental Science, Psychology, Economics, Management, Education, Humanities — 11 disciplines with no Plot Studio capability mapping |
| **Grouping mismatch** | S2 uses "Biology / Medicine" as one card; S1 lists them separately |

**Decision needed:** one canonical roster of 20 (adding Materials Science), and capability mappings
for the 11 uncovered disciplines.
**Impact:** `discipline_profiles` seed data; terminology rule scoping; default test/graph selection.
**Note:** the 11 unmapped disciplines are mostly covered by the *universal* capabilities (XY, line,
column, regression, correlation) — only discipline-specific defaults are missing.

## Q4 — Plotly vs Matplotlib: where does rendering happen? (ambiguity, S2 §15)

Both libraries are in the stack with no split point defined. Three plausible architectures:

| Option | Plotly role | Matplotlib role | Cost |
|--------|-------------|-----------------|------|
| **A. Dual** | Interactive canvas in-browser | Server-side static export | Two rendering paths must stay visually identical — hard |
| **B. Server-only** | — | All rendering, Plotly for static export | Slow interactive editing; Plotly is redundant |
| **C. Client-only** | Everything interactive | — | Loses the export engine's server-side determinism |

**Recommendation:** Option A, with Matplotlib as the single source of truth for exported output and
Plotly as a preview that is re-rendered server-side on export. Accept that preview and export may
differ subtly; journal compliance depends on the export path only.
**Impact:** the entire Graph Editor, the export engine, and §13 reproducibility (which requires
deterministic output — favouring server-side).

## Q5 — Evidence Matrix and Data traceability (omission, S2 §18)

Two capabilities appear in the architecture diagram and nowhere else:
- **Evidence Matrix** (Literature, L925) — a table mapping claims to supporting evidence/citations.
  Never defined. No requirements, no UI, no entity.
- **Data traceability** (Integrity, L934) — named as an Integrity responsibility, but the only
  concrete implementation given is the §13 provenance panel, which covers figures, not claims.

**Decision needed:** define the Evidence Matrix, or remove it from the diagram. It is a substantial
feature with real value for systematic-review work — but it cannot be built from a diagram label.
**Impact:** scope of the Literature module and the Integrity layer.

## Q6 — Entity naming inconsistency (contradiction, both sources)

| S1 | S2 | Likely |
|----|----|--------|
| `journal_settings` | `journal_presets` | same entity |
| `revisions` | `versions` | same entity |
| `analyses` | `statistical_analyses` | same entity |

**Decision needed:** canonical names. **Recommendation:** prefer the S2 names — they are more
specific and were written later, against a fuller schema.
**Impact:** schema, API paths, code imports.

## Q7 — Two overlapping figure-checking systems (ambiguity, both sources)

| | Plot Studio §12 | Manuscript checker §FIGURES |
|---|-----------------|--------------------------|
| Scope | one figure | the manuscript's figure set |
| Count | 12 checks | 5 checks |
| Focus | scientific completeness | numbering, captions, citation, resolution, axis labels |
| Overlap | resolution, axis labels | |

Resolution and axis labels appear in both.

**Decision needed:** do they share an implementation, or run independently? Does one consume the
other's results?
**Recommendation:** implement the 12-check audit once, in Plot Studio, persisting results to
`figure_audits`. The manuscript checker's FIGURES dimension then *reads* those results for checks 8
(resolution) and 9 (axis labels) and adds its own three (numbering, captions, in-text references).
One source of truth, no duplicate logic.
**Impact:** both modules' API design.

## Q8 — Journal preset maintenance (gap, S2 §10)

§10 requires each rule to carry its **source** and **date** — "rather than silently assuming
outdated rules". But nothing describes how presets get created, verified, or updated.

**Decision needed:** who updates journal presets? Manual admin entry? Scraped from journal sites
with periodic re-verification? Seeded and frozen at launch?
**Recommendation:** seeded + admin-editable, with `rule_verified_at` mandatory and a staleness
warning in the UI. Do not scrape — journal sites vary and scraping breaks silently.
**Impact:** needs an admin surface (Stage 4 scope pulled forward), plus a trust UI for showing
source and date.

## Q9 — Non-functional requirements: entirely absent (gap, both sources)

Neither document specifies any of:

| Missing | Why it matters |
|---------|----------------|
| **File format support** | `.xlsx` is shown (§03); what about `.csv`, `.txt`, `.tsv`, `.json`? |
| **Max upload size / row count** | The status bar shows `Rows: 120`, implying scale matters |
| **Concurrency** | Collaboration is a Stage 2 feature — needs a concurrency model |
| **Performance targets** | No latency or throughput requirement anywhere |
| **Offline / large-file mode** | Spectroscopy and NGS datasets can be enormous |
| **Accessibility** | No WCAG target stated |
| **Browser support** | Neither document states it |
| **Security / compliance** | No threat model; no data-residency story for Stage 4 institutions |
| **Internationalisation** | 19 disciplines implies international users; UI language strategy unstated |
| **Retention / deletion policy** | Required for institutional data governance |

**Recommendation:** treat as engineering-decidable, but write them down before Stage 1 exit.

## Q10 — Writing module storage model: entirely absent (gap, S1 vs S2)

S2's 19-entity schema contains **no manuscript entities at all** — no `manuscripts`, `sections`,
`revisions`, `tables`, or `references`. Yet S1 names all five, defines an `/api/manuscripts`
endpoint, and the Writing module is half the product. S2 — despite being the longer, later, more
detailed document — models only Plot Studio.

**Decision needed:** the manuscript/section/revision schema, the revision-diff model, and how a
manuscript section references the figures it cites.
**Impact:** **blocking.** The Writing module and the §checker cannot be built without it.
**Recommendation:** see [05-data-model.md](./05-data-model.md) §5.3 "Entities required but absent".

## Q11 — How is cell data actually stored? (gap, S2 §16)

S2 names `columns` (metadata) but no entity holds cell values. A 120×8 sheet is 960 values; a real
dataset can be millions.

**Decision needed:** wide table (`rows` + `values jsonb`), columnar (`column_values` with
compression), or a `pyarrow`/Parquet sidecar in object storage with only statistics in Postgres?
**Recommendation:** Parquet in object storage + statistics and roles in Postgres. Keeps Postgres
small, makes Trace and Transform efficient, and scales to spectroscopy/NGS volumes. Introduces a
second storage system — accept it deliberately.
**Impact:** performance, storage cost, the Transform and Trace implementations.

## Q12 — Do audit failures block export? (gap, S2 §12)

12 checks; the source shows one failing (`Y-axis unit has not been specified`) but does not say
whether export proceeds.

**Recommendation:** warn, never hard-block, except for a narrow set. Hard-blocking on "legend
present" is wrong for single-series figures; hard-blocking on "units specified" is defensible.
Design: each check carries a severity (`info` / `warn` / `block`), defaulting most to `warn`, with
`units specified` and `statistical values calculated` as the only candidates for `block`.
**Impact:** export UX, and how much friction the integrity feature adds.

## Q13 — Likert-scale / ordinal data handling (gap, S2 §14)

"Likert-scale analysis" is named as a Social Sciences capability but no supporting mechanism
exists: no ordinal data type, no median/IQR reporting, no appropriate correlation default.

**Recommendation:** add an `ordinal` column data type, default to median + IQR for descriptive
statistics on ordinal data, and default correlation to Spearman. Small, contained, and required
for the Social Sciences claim to be honest.

## Q14 — "Layered graphs" undefined (gap, S2 R4)

RELEASE 4 lists "layered graphs" with no definition. Not in the graph type registry (§5.6), not in
the PLOT menu, not in the wizard.

**Likely meaning:** multi-y-axis plots, or overlaid/composited plot layers with independent axes.
**Decision needed:** confirm intent, then add to the type registry.
**Impact:** scope of RELEASE 4; the `graphs` model may need a child layer table.

## Q15 — Collaboration mechanics (gap, S1 Stage 2)

"Collaboration" is a Stage 2 deliverable with no further specification. No presence model, no
conflict resolution, no comment/annotation entity, no permission levels.

**Recommendation:** real-time co-editing is expensive and out of scope for Stage 2. Deliver
**asynchronous** collaboration first: `versions` history, per-section authorship, and a
comment/annotation thread on sections and figures. Add live cursors only if Stage 2 slips into
Stage 3.
**Impact:** Stage 2 scope; whether a CRDT library (Yjs, Automerge) is needed at all.

## Q16 — Acceptance, Edit and the "Edit" path (gap, S1 L256)

The hero card offers **Edit** as a first-class action alongside Accept and Reject, but nothing
defines it. Editing a *suggestion* and editing the *text* are different operations with different
audit implications.

**Decision needed:** does Edit open the suggestion for modification before applying, or open the
surrounding paragraph for direct editing?
**Recommendation:** Edit opens the suggestion in a small inline editor with Apply/Cancel. The
resulting change is still `attribution = SOFTWARE` (the suggestion came from software) but with
`decision = 'edit'` and the human's final text stored. A direct paragraph edit is a separate
`attribution = HUMAN` action.
**Impact:** suggestion UX, audit semantics — and therefore the honesty of the authorship record.

## Q17 — Rejected-suggestion persistence (gap, S1)

Repeatedly rejecting the same false positive is a real failure mode for a tool meant to be run
often. Nothing in the source addresses it.

**Recommendation:** `suggestion_rejections` table keyed on (user, rule, normalised context). A
rejected suggestion is suppressed until the underlying text changes. Needs a "show dismissed
suggestions" escape hatch.
**Impact:** schema, writing-engine behaviour.

## Q18 — Curve-fit and statistical-significance reporting format (gap)

§06 requires 9 outputs per fit; §08 requires markers in `*`/`**`/`***`/`****`/`ns`/`p = 0.032`/
`p < 0.001`. Nothing specifies output format, precision, or which fields are required.

**Decision needed:** decimal places, rounding, whether CI bounds are shown, whether "significant"
uses `< 0.05` or the configured `significance_level`.
**Recommendation:** store full precision in `statistical_analyses.results`; format only at render
time; make `significance_level` a per-analysis field (already in
[05-data-model.md](./05-data-model.md)) rather than a global constant; default 0.05.
**Impact:** rendering, export, and reproducibility — a figure's numbers must not change if a global
default is later altered.

---

## Summary table

| # | Type | Source | Blocks | Priority |
|---|------|--------|--------|----------|
| Q10 | Omission | S1 vs S2 | Writing module entirely | **Critical** |
| Q11 | Omission | S2 §16 | Data layer performance | **Critical** |
| Q1 | Contradiction | S2 §01 vs §02 | Navigation | High |
| Q3 | Contradiction | S1 vs S2 | Discipline profiles | High |
| Q5 | Omission | S2 §18 | Literature scope | High |
| Q4 | Ambiguity | S2 §15 | Graph editor, export | High |
| Q6 | Contradiction | S1 vs S2 | Naming only | Medium |
| Q7 | Ambiguity | both | Checker design | Medium |
| Q8 | Omission | S2 §10 | Journal presets | Medium |
| Q9 | Omission | both | Everything | Medium |
| Q16 | Omission | S1 L256 | Suggestion UX | Medium |
| Q17 | Omission | S1 | Writing engine | Medium |
| Q18 | Omission | S2 §06, §08 | Number formatting | Medium |
| Q12 | Omission | S2 §12 | Export UX | Low |
| Q13 | Omission | S2 §14 | Social Sciences claim | Low |
| Q14 | Omission | S2 R4 | RELEASE 4 scope | Low |
| Q15 | Omission | S1 Stage 2 | Stage 2 scope | Low |
| Q2 | Ambiguity | both | Branding | Low |

## Three decisions that cannot wait

1. **Q10** — the Writing module has no data model. Half the product is unspecified at the storage
   layer.
2. **Q11** — cell storage strategy determines the schema, the Transform engine and Trace. Changing
   it later means rewriting all three.
3. **`data_transformations` must be an ordered replayable log, and `audit_logs.attribution` must be
   `NOT NULL`, in the very first migration.** Neither can be retrofitted. Retrofitting attribution
   means history that was never attributed — exactly the failure this product exists to prevent.
