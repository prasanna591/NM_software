# 11 — Build Strategy

How to build this effectively. Derived from the 12 documents in this folder. This is a strategy
document, not a specification — it contains opinion and recommendation, clearly marked.

---

## 11.1 The honest sizing problem

Before anything else, the scale has to be stated plainly.

| Product | Age | Engineering effort |
|---------|-----|--------------------|
| Origin (OriginLab) | ~30 years | Dozens of engineers, decades |
| GraphPad Prism | ~20 years | Decades, niche-priority company |
| **SCIX as specified** | 0 | S2 alone specifies 19 graph types, 21 statistical tests, 9 curve-fit models, peak analysis, multi-panel figure design, journal presets, 10 disciplines of plotting |

You cannot out-build Origin feature-for-feature. Attempting it is the most likely way this project
fails — you spend three years on a plotting engine and arrive at a worse Origin.

**The specification is not the roadmap.** 18 sections of Plot Studio describe the destination. The
build plan must describe a path to a defensible subset.

---

## 11.2 The reframe: this is three products

The spec bundles three products that share almost no code:

| # | Product | Difficulty | Competitive position |
|---|---------|-----------|---------------------|
| **A** | Scientific writing assistant | **Very hard** — language quality is the whole product | Crowded (Grammarly, LanguageTool, Writefull) |
| **B** | Origin/Prism-class plotting + statistics | **Very hard** — 30 years of work | Entrenched, expensive incumbents |
| **C** | Research-integrity / submission-compliance layer | **Moderate** — mostly data modelling | **Nearly unoccupied** |

### Recommendation: build C first, and let A and B feed it

Products A and B are **commodity**. SciPy already does the statistics. Plotly already does the
plotting. LanguageTool already does the grammar. You will never beat Origin at plotting, and you
should not try.

Product C is where the defensibility lives, and — this is the key observation — **C is mostly a data
modelling problem, not an algorithms problem**. An audit trail, a provenance chain, a reproducibility
record, a journal-compliance check: these are schema and workflow, not hard science. That makes C
simultaneously the cheapest to build well and the hardest for a competitor to copy cheaply, because
copying it requires rebuilding their entire data model retroactively — which they cannot do without
rewriting their history.

### The strategic wedge

> **Do not compete on the first mile. Own the last mile.**

Origin owns data → plot. Prism owns statistics → plot. **Nobody credibly owns
plot → manuscript → submission package → defensible audit record.** That is where a new entrant can
win, because incumbents would have to destroy their own installed base to follow.

Concretely, the researcher does not adopt a tool because the plot editor is nice. They adopt it
because **the submission went through and nobody questioned the figures.**

---

## 11.3 Build vs. buy — per subsystem

Most of the specification can be assembled from mature open source. Only the glue is yours.

| Subsystem | Source spec | Recommendation | Licence note |
|-----------|-------------|----------------|--------------|
| Grammar + spelling | S1 tool 01 | **LanguageTool** — do not build | LGPL; Python API; custom rule patterns; 30+ languages |
| Sentence formation | S1 tool 02 | LanguageTool + constrained rewrite | |
| Register / style | S1 tool 03 | Custom rules — it is option-driven, not AI-driven | |
| Paragraph structure | S1 tool 04 | Custom — heuristics are sufficient | |
| Terminology consistency | S1 tools 05–06 | **Build** — this is discipline-data, your moat | |
| Manuscript 5-dim checker | S1 §checker | Build on top of the above | |
| Statistics (21 tests) | S2 §07 | **SciPy + Statsmodels + pingouin** | BSD |
| Curve fitting (9 models) | S2 §06 | `scipy.optimize.curve_fit`, **lmfit** | BSD/MIT |
| Peak analysis | S2 §06 | `scipy.signal.find_peaks`, lmfit | BSD |
| Interactive canvas | S2 §15 | **Plotly** | MIT |
| Static export | S2 §15 | **Matplotlib** | PSF-like |
| DOCX export | S1 API | **python-docx** | MIT |
| PPTX export | S2 §02 | **python-pptx** | MIT |
| LaTeX export | S1/S2 | **Pandoc** + template | GPL-2 — invoke as a binary, do not link |
| PDF export | S1 API | LaTeX/WeasyPrint | |
| DOI verification | S2 §18 | **CrossRef / DataCite REST lookup** | see §11.7 |
| Auth | — | Build, or Auth0/Keycloak at Stage 4 | |
| File storage | — | S3/MinIO + **Parquet** | Apache-2.0 |

**Estimated effect:** roughly 60–70% of the specified functionality is reachable by assembling
libraries. That is what makes a 12-month publication-grade product feasible for a small team, and
also why it cannot be differentiated on features.

---

## 11.4 The architecture that makes it work: one thin vertical slice

Do not build modules. Build **one figure, all the way through the chain**.

### The slice

Discipline: **Chemistry only** · Graph: **XY line with error bars** · Analysis: **one-way ANOVA +
Tukey** · Export: **600 DPI PNG + PDF**

Everything else is deferred. But this slice must include:

```
Upload .xlsx
  → Parse to Parquet, worksheet + typed columns
  → One transformation (normalise)
  → One-way ANOVA, user-selected, stored with library version
  → Significance markers derived from that stored analysis
  → Format axes, units, legend
  → Figure audit — all 12 checks, one deliberately failing
  → Export PNG/PDF at 600 DPI
  → Provenance panel showing all 9 fields
  → Trace Figure → back to the source dataset
  → Every step written to audit_logs with attribution
```

### Why this specific slice

- It exercises **every table** in the 24-entity model
- It exercises **every integrity constraint** — `attribution NOT NULL`, `source_analysis_id` on
  significance annotations, ordered `data_transformations`
- It is small enough to finish in 6–8 weeks
- It produces a screenshot that demonstrates the product's actual differentiator

### The gate

> **Do not proceed to Phase 2 until the §6.11 traceability chain works end-to-end for one figure.**

If the chain is broken at any link, the architecture is wrong, and every subsequent feature
compounds the error. This is the single most important gate in the entire plan.

### Why Chemistry first

- Both source documents lead with chemistry examples (`CeNiO₃`, `UV–Vis`, `Experiment_01.xlsx`,
  "Nanomaterial Study")
- The terminology rules are concrete and checkable — formulas, subscripts, dash style, unit spacing
- The plot types are well-defined — spectra, XRD patterns, kinetics, calibration curves
- Journal figure requirements are published and findable
- It is the hardest discipline for terminology, so a design that works there works everywhere

---

## 11.5 The discipline profile trap

S1 promises 19 disciplines. Building 19 discipline implementations is 19× the work and guarantees
none of them are good.

**Recommendation:**

1. Build **one** discipline profile, hardcoded, for Chemistry
2. Get the *shape* right — everything discipline-specific behind a profile interface
3. Add the other 18 **as YAML/JSON data only**, no new code
4. If a profile genuinely cannot be expressed as data, that is a signal the abstraction is wrong —
   fix it before adding profile 3

A discipline profile is four things (per S1 L421): terminology rules, manuscript template, preferred
statistical tests, journal formats. All four are data. If your profile needs code, redesign it.

---

## 11.6 The LLM question

The product is positioned *against* AI authorship (S1 L354: "this is what separates a writing
assistant from an AI humanizer"). But the invariant forbids generating *scientific claims*, not
correcting *language*. Those are different things, and the distinction is exploitable.

### Recommendation: use an LLM for language-only tasks, guarded by a deterministic invariant checker

Permitted, because it changes only how something is said:
- grammar and sentence repair
- register and readability rewriting
- terminology disambiguation *within* a fixed candidate set

Forbidden, always:
- anything that touches a number, unit, formula, gene symbol, citation or directional claim

### The guard: semantic invariant checker

This is the important engineering idea, and it is what makes LLM use honest here.

For any proposed rewrite, extract a **scientific token set** from before and after:

| Token class | Extraction |
|------------|-----------|
| Numbers + units | `10 mg`, `0.05`, `37 °C` |
| Chemical formulas | `CeNiO3`, `H2SO4` |
| Gene / protein symbols | `[A-Z][a-z]{2,}` in context, `IL-6`, `p53` |
| Citations | `[12]`, `(Smith et al., 2020)`, `doi:…` |
| Direction / magnitude | increase, decrease, higher, lower, significant, "3-fold" |
| Domain proper nouns | anything in the discipline termbase |

Then, before presenting the suggestion:

```
if extract(before) != extract(after):
    → either REJECT the rewrite, or
    → present it flagged, requiring explicit human confirmation,
        with the changed tokens highlighted and named
```

This is fully implementable, fully auditable, deterministic, and testable. It converts the LLM from
an unpredictable content source into a **language-only transform with a proven invariant**. It is
also the strongest possible answer to the "is this AI-generated?" question: you can show that no
scientific token changed.

Without this checker, an LLM in the loop will eventually turn "increased by 12%" into "increased by
21%" and the product's central claim becomes false. With it, the claim is mechanically defensible.

### Practical guidance

- Keep the LLM behind an interface where the only permitted operations are the three above
- Log every model call in `audit_logs` with `actor_component = 'llm'` and the model version
  (reproducibility — same rule as `library_version` for stats)
- Rule-based first, LLM fallback: try LanguageTool, escalate to the LLM only for what rules cannot
  handle. Cheaper, faster, and more predictable
- Never let the LLM see the reference list and never let it produce a citation (rule R4)

---

## 11.7 References: verify, never generate

Rule R4 bans AI-generated references. But there is a large, legitimate adjacent capability:

**A user supplies a DOI. The system validates it against CrossRef/DataCite and fills the metadata
from the registry.**

This is not generation — it is verification against an authoritative source. It catches:
- mistyped DOIs
- duplicated references in the bibliography
- inconsistent metadata across entries

It is enormously valuable to researchers and produces zero fabricated citations. Make the boundary
explicit in the code and the UI: *the registry confirms; it never invents.* A user may paste a
reference with **no** DOI — the system formats it and flags it as unverified, and never invents
metadata to fill the gap.

---

## 11.8 Phased plan with gates

### Phase 0 — Foundations (2–3 weeks)

Resolve the blocking questions first. Specifically **Q10** (manuscript schema) and **Q11** (cell
storage), because both determine the schema and are expensive to change.

- Decide Q10, Q11, Q4 (Plotly vs Matplotlib), Q1 (navigation), Q3 (discipline roster)
- Repository: monorepo — `frontend/`, `backend/`, `engine/`, `profiles/`, `docs/`
- **Migration #1** with the non-retrofittable constraints:
  - `audit_logs.attribution NOT NULL`
  - `data_transformations` ordered and replayable (`seq`, `transform_type`, `params`)
  - `statistical_analyses.library_version NOT NULL`
  - `graph_annotations.source_analysis_id NOT NULL` when `kind='significance'`
  - `journal_presets.rule_source` + `rule_verified_at NOT NULL`
- CI: lint, typecheck, migrations, tests

**Gate:** schema reviewed; invariant constraints present in the first migration, not added later.

### Phase 1 — The vertical slice (6–8 weeks)

As defined in §11.4. Chemistry only, one graph type, one analysis.

**Gate:** traceability chain works end-to-end for one figure. Figure audit passes and can fail.
Trace navigates back to the source file. Every action in `audit_logs` with correct attribution.

### Phase 2 — Writing MVP (8–10 weeks)

- `manuscripts` / `sections` schema (resolves Q10)
- Editor with the diff/track-changes component from S1 — accept / edit / reject
- LanguageTool for grammar and spelling
- Terminology + consistency checker (data-driven rules)
- `versions` with per-change attribution
- Journal presets seeded with real verified requirements for a handful of journals

**Gate:** a non-native researcher writes a paragraph, accepts some suggestions, rejects others, and
every single change is attributable with the correct HUMAN/SOFTWARE label.

### Phase 3 — Discipline profiles as data (3–4 weeks)

Convert Chemistry to a data profile. Add the remaining 18 as data. Validate on three deliberately
different domains — Physics, Computer Science, Social Sciences — to prove the abstraction.

**Gate:** three disciplines work correctly with **zero new application code**.

### Phase 4 — Publication (8–10 weeks)

- `figures` + `figure_panels`, multi-panel designer
- Export Center: DOCX, PDF, LaTeX, PPTX, with figures embedded and provenance attached
- Manuscript ↔ figure integration
- The 5-dimension pre-submission checker

**Gate:** a complete manuscript with figures exports and passes the pre-submission checker.

### Phase 5 — Statistical and plotting depth (parallel, ongoing)

- Remaining graph types, remaining tests, curve fitting, peak analysis
- Batch plotting, templates, peak workflows

This phase is open-ended and can absorb the team's remaining capacity indefinitely. It is the
phase where "good enough to publish" becomes "competitive with Prism", and it does not gate the
product's launch.

### Phase 6 — Institutional (S1 Stage 4)

Institutions, roles, labs, supervisor dashboards, repositories. Only after product-market fit.

---

## 11.9 Critical path

From [08-roadmap.md](./08-roadmap.md) §8.6, with the additions this strategy implies:

```
Schema + invariants (Phase 0)   ← everything depends on this
  → Cell storage decision (Q11)
  → Data layer: upload, worksheet, columns
  → Ordered transformation log              ← Trace depends on this
  → statistical_analyses + library versions  ← significance markers depend on this
  → audit_logs + attribution                ← the product's moat
  → Graph render + export
  → Figure audit + provenance + Trace       ← THE GATE
  → Manuscript schema (Q10)
  → Writing engine + diff/accept/reject
  → figures + figure_panels + Export Center
  → Discipline profiles as data
```

Two items cannot be parallelised or deferred:
- **`data_transformations` must be an ordered log from day one.** Retrofitting order into a
  flag-based design means rewriting the provenance chain after every figure already exists.
- **`attribution` must be `NOT NULL` in migration #1.** Retrofitting attribution means history
  that was never attributed — precisely the failure this product exists to prevent.

---

## 11.10 What not to build

Explicit anti-scope. Each of these looks reasonable and will consume the project.

| Do not build | Why |
|--------------|-----|
| A scientific-English grammar checker | LanguageTool already exists, is free, and has 30+ languages. Multi-year trap. |
| All 19 graph types before validating the model | If `graphs` is wrong, 19 types are 19 wrong implementations. |
| All 19 discipline profiles as code | §11.5. Data, not code. |
| Real-time collaborative editing (CRDT/Yjs) | Expensive. Ship asynchronous version history + comments first (Q15). |
| The Evidence Matrix | Named once in a diagram, defined nowhere. Specify it or drop it (Q5). |
| Journal-preset scraping | Sites break silently. Seed + admin-edit + verification date. |
| Both Plotly and Matplotlib as authorities | Two rendering paths that disagree. Pick one source of truth for output (Q4). |
| "Layered graphs" | Undefined in the spec (Q14). Do not guess. |
| Own DOCX/PPTX/PDF writers | `python-docx`, `python-pptx`, Pandoc. Mature. |
| A general-purpose literature manager | The spec names DOI, PDF and Evidence Matrix. Build those three. |
| Any form of automated scientific content generation | Explicitly forbidden. Not a priority decision — a product invariant. |

---

## 11.11 Team and timeline

### Skills required

| Role | Needed for | Cannot be skipped |
|------|-----------|-------------------|
| Scientific Python (SciPy/Statsmodels/NumPy) | engine, statistics, curve fitting, peak analysis | Yes |
| Backend (FastAPI, schema, migrations) | API, data model, provenance | Yes |
| Frontend (React/Next.js, **Plotly**) | editor, property panel, canvas | Yes |
| Frontend/graphics (Matplotlib, fonts, DPI, SVG/PDF) | journal-compliant export | Yes — this is where publication quality is won or lost |
| Computational linguistics / language tooling | terminology rules, style checks | Partial — LanguageTool covers the base |
| Scientific-domain knowledge | discipline profiles, journal requirements | Yes, per discipline |
| Product/design | the diff interaction is the product | Yes |

### Honest timeline

| Milestone | 3 strong devs | 6 devs |
|-----------|---------------|--------|
| Vertical slice proves architecture | 3–4 months | 6–8 weeks |
| MVP (Stage 1) usable by real researchers | 5–7 months | 3–4 months |
| Publication-grade (Stage 3) | 14–20 months | 9–12 months |
| Competitive with Prism on statistics | 2–3 years | 12–18 months |
| Competitive with Origin on plotting | Do not plan for this | 3–5 years |

The last row is the one to internalise. It is why §11.2 says own the last mile.

---

## 11.12 Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | Scope: attempts to match Origin feature-for-feature | **High** | Fatal | §11.2 wedge; §11.10 anti-scope; Phase 5 is explicitly open-ended |
| 2 | Q10/Q11 unresolved → schema rewrite after data exists | Medium | **Severe** | Resolve in Phase 0, before migration #1 |
| 3 | Retrofitting attribution or transform ordering | Medium | **Severe** | Both in migration #1. Enforce in code review. |
| 4 | Incumbent ships a competitor feature fast (Writefull, etc.) | High | Medium | Compete on integrity/compliance, which is structural, not feature-level |
| 5 | Language quality judged as poor → writing module loses trust | Medium | High | LanguageTool baseline + LLM only behind the invariant checker; narrow claims |
| 6 | LLM changes a scientific value → invariant broken | Medium | **Severe** | §11.6 token-extraction checker, mandatory, tested as a security control |
| 7 | 19 discipline profiles are shallow and unconvincing | High | Medium | Ship fewer, deeper profiles; a good Chemistry beats 19 thin ones |
| 8 | Journal presets go stale → compliance claims become false | High | Medium | `rule_verified_at` mandatory + visible staleness warning; never scrape |
| 9 | Plotly/Matplotlib divergence → preview ≠ export | High | Medium | Single export authority; visual regression tests on export fixtures |
| 10 | Under-resourced statistics depth | Medium | High | Ship SciPy/Statsmodels directly with clear provenance; depth is Phase 5 |
| 11 | Key person leaves mid-project | Low | High | The data model *is* the institutional knowledge; it is documented in `docs/` |
| 12 | Nobody can articulate the differentiator | Medium | High | If this document's §11.2 wedge is not persuasive internally, the project has no thesis |

---

## 11.13 The five things that matter most

If this document is read six months from now and only five points survive, these are they.

1. **Own the last mile.** Plot → manuscript → submission → defensible record. Do not compete on
   plotting; Origin wins that permanently.

2. **The traceability chain is the product.** Everything else is table stakes. §6.11 is the
   acceptance criterion for the whole platform.

3. **Migration #1 is irreversible.** `attribution NOT NULL` and ordered `data_transformations`.
   Nothing else in the schema matters as much.

4. **One figure, all the way through.** Not nineteen graph types shallowly. One figure with a
   complete, working provenance chain proves the architecture; nothing else does.

5. **Disciplines are data.** One profile in code, eighteen in YAML. The moment a discipline needs
   an `if statement`, the abstraction has failed.

---

## 11.14 Immediate next actions

| # | Action | Output |
|---|--------|--------|
| 1 | Answer Q10 — design `manuscripts` / `sections` / `revisions` / `references` | Schema fragment in `docs/05-data-model.md` |
| 2 | Answer Q11 — choose cell storage | ADR: Parquet sidecar vs. Postgres values |
| 3 | Answer Q4 — decide the render split | ADR: Matplotlib as export authority |
| 4 | Draft migration #1 | SQL with all five invariant constraints |
| 5 | Stand up the monorepo + CI | `frontend/`, `backend/`, `engine/`, `profiles/`, `docs/` |
| 6 | Build the Chemistry profile schema | YAML shape validated against S1's four dimensions |
| 7 | LanguageTool spike | Confirm it handles academic English adequately; decide the LLM escalation boundary |
| 8 | Build the §11.4 slice | The gate |

Items 1–4 are the true blockers. Nothing else should start until they are closed.
