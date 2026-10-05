# 08 — Roadmap

Two independent roadmaps appear in the sources. This document merges them into one sequenced plan.

- **S1 §How It Gets Built (L433–460)** — 4 platform **stages**, product-level
- **S2 §18 (L942–968)** — 5 Plot Studio **releases**, module-level

---

## 8.1 S1 — four platform stages

**Heading (L436):** Four stages — starting with a working MVP, not the whole platform

| Stage | Title | Scope |
|-------|-------|-------|
| **STAGE 1 — MVP** | Prove the workflow | Editor, projects, grammar & sentence correction, data upload, basic graphs and tables |
| **STAGE 2 — RESEARCH PLATFORM** | Add depth | Statistics, references, literature management, version control, collaboration |
| **STAGE 3 — PUBLICATION PLATFORM** | Get to submission | Journal formatting, DOCX/PDF/LaTeX export, submission prep, research-integrity checks |
| **STAGE 4 — INSTITUTIONAL PLATFORM** | Scale to labs | University accounts, research labs, supervisor dashboards, institutional repositories, admin |

## 8.2 S2 — five Plot Studio releases

**Heading (L941):** Recommended development priority

| Release | Title | Scope |
|---------|-------|-------|
| **RELEASE 1 — CORE** | Foundation | Data table, import, basic graphs, formatting, PNG/PDF export |
| **RELEASE 2 — SCIENTIFIC** | Analytical depth | Regression, error bars, curve fitting, statistics, publication-quality export |
| **RELEASE 3 — PRISM-STYLE** | Statistical workflow | ANOVA, t-tests, multiple comparisons, dose-response, survival, ROC |
| **RELEASE 4 — ORIGIN-STYLE** | Advanced plotting | Advanced fitting, peak analysis, layered graphs, batch plotting, templates |
| **RELEASE 5 — RESEARCH INTELLIGENCE** | Integrity layer | Figure audit, reproducibility, journal presets, manuscript integration, full audit trail |

## 8.3 Merged sequencing

Mapping S2 releases onto S1 stages. This is derived, not stated — but it is the only ordering that
satisfies both documents.

| Platform stage | Plot Studio releases | Cumulative deliverable |
|---------------|---------------------|------------------------|
| **STAGE 1 — MVP** | RELEASE 1 — CORE | End-to-end: project → upload data → table → basic graph → PNG/PDF. Plus Writing MVP: editor, projects, grammar, sentence correction. |
| **STAGE 2 — RESEARCH PLATFORM** | RELEASE 2 — SCIENTIFIC, RELEASE 3 — PRISM-STYLE | Full statistical workflow. Plus references, literature management, version control, collaboration. |
| **STAGE 3 — PUBLICATION PLATFORM** | RELEASE 4 — ORIGIN-STYLE (partially), RELEASE 5 — RESEARCH INTELLIGENCE | Journal formatting, DOCX/PDF/LaTeX export, submission prep, integrity checks, advanced plotting. |
| **STAGE 4 — INSTITUCIAL PLATFORM** | — | University accounts, labs, supervisor dashboards, institutional repositories, admin. |

### Notable consequences

1. **The figure audit is deferred to Stage 3.** RELEASE 5 is the last Plot Studio release. This is
   defensible — the integrity layer needs the version control and provenance foundations from
   Stage 2 — but it means the product's *claimed differentiator* is not present in the MVP. Worth a
   conscious decision: see §8.6.

2. **Statistics arrive before publication tooling.** RELEASE 3 (statistics) precedes RELEASE 5
   (integrity), which matches S1's Stage 2 → Stage 3 order. Consistent.

3. **Batch plotting (RELEASE 4) has no S1 counterpart.** It is a Plot-Studio-only capability —
   applying one plot spec across many worksheets/datasets. Requires the template system to be
   genuinely parameterised.

4. **Layered graphs (RELEASE 4)** also appear only in S2. "Layered" = multi-y-axis / overlay
   composition. Not modelled in §5.6's graph type registry — gap, see Q14.

## 8.4 Stage-by-stage deliverable breakdown

### STAGE 1 — MVP · Prove the workflow

**Platform (S1):** Editor · Projects · Grammar & sentence correction · Data upload · Basic graphs
and tables

**Plot Studio (RELEASE 1):** Data table · Import · Basic graphs · Formatting · PNG/PDF export

**Infrastructure:** Next.js shell · FastAPI service · PostgreSQL schema · `users`/`projects`/
`datasets`/`columns`/`graphs` · basic auth · object storage

**Acceptance test:** a researcher creates a project, uploads a spreadsheet, makes a line plot with
error bars, formats the axes, exports a 600-DPI PNG, and gets grammar corrections on a paragraph of
text — all inside the platform.

### STAGE 2 — RESEARCH PLATFORM · Add depth

**Platform (S1):** Statistics · References · Literature management · Version control ·
Collaboration

**Plot Studio (RELEASE 2 + 3):** Regression · Error bars · Curve fitting · Statistics ·
Publication-quality export · ANOVA · t-tests · Multiple comparisons · Dose-response · Survival ·
ROC

**Adds:** `statistical_analyses` + `analysis_parameters` + `data_transformations` · `versions` ·
`references` · the 21-test registry · Prism-style wizard · statistical annotation

**Acceptance test:** the researcher runs a one-way ANOVA with Tukey post-hoc, sees the result in the
properties panel, sees significance markers appear on the plot derived from that analysis, and can
roll back any change.

### STAGE 3 — PUBLICATION PLATFORM · Get to submission

**Platform (S1):** Journal formatting · DOCX/PDF/LaTeX export · Submission prep ·
Research-integrity checks

**Plot Studio (RELEASE 4 + 5):** Advanced fitting · Peak analysis · Layered graphs · Batch
plotting · Templates · Figure audit · Reproducibility · Journal presets · Manuscript integration ·
Full audit trail

**Adds:** `figures` + `figure_panels` + `journal_presets` + `exports` + `audit_logs` ·
publication figure designer · figure audit (§12) · provenance panel + Trace (§13) · Export Center

**Acceptance test:** a figure passes the 12-point audit, its provenance record traces back to the
source dataset, journal preset rules are applied with visible sources and dates, and the manuscript
exports to DOCX/PDF/LaTeX with figures embedded and an audit trail attached.

### STAGE 4 — INSTITUCIAL PLATFORM · Scale to labs

**Platform (S1):** University accounts · Research labs · Supervisor dashboards · Institutional
repositories · Admin

**Adds:** `institutions` · tenancy model · roles (`researcher` / `supervisor` / `admin`) · lab
scoping of projects · supervisor read-only oversight views · repository deposit

**Acceptance test:** a university admin provisions lab accounts; a supervisor sees all lab projects
and their audit trails without being able to edit them; a completed project is deposited in the
institutional repository.

## 8.5 Feature-to-release traceability

| Feature | Source section | S1 stage | S2 release |
|---------|---------------|----------|------------|
| Project management | S1 arch | 1 | — |
| Manuscript editor | S1 arch | 1 | — |
| Grammar correction | S1 tool 01 | 1 | — |
| Sentence formation | S1 tool 02 | 1 | — |
| Data upload / import | S1 API, S2 §03 | 1 | R1 |
| Data table / worksheet | S2 §03 | 1 | R1 |
| Column metadata & roles | S2 §03 | 1 | R1 |
| Basic graphs (XY/line/scatter/column) | S2 §02 | 1 | R1 |
| Graph formatting | S2 §02, §05 | 1 | R1 |
| PNG / PDF export | S2 §02 | 1 | R1 |
| Basic tables | S1 stage 1 | 1 | — |
| Scientific language improvement | S1 tool 03 | 2 | — |
| Paragraph checking | S1 tool 04 | 2 | — |
| Terminology checker | S1 tool 05 | 2 | — |
| Consistency checker | S1 tool 06 | 2 | — |
| Pre-submission checker (5 dimensions) | S1 §checker | 2–3 | — |
| Statistics (21-test registry) | S2 §07 | 2 | R2, R3 |
| Curve fitting (9 models) | S2 §06 | 2 | R2 |
| Error bars | S2 §02 | 2 | R2 |
| Regression | S2 §02 | 2 | R2 |
| Publication-quality export | S2 R2 | 2 | R2 |
| Dose-response, Survival, ROC | S2 §07 | 2 | R3 |
| References | S1 API | 2 | — |
| Literature management | S1 stage 2 | 2 | — |
| Version control | S1 stage 2 | 2 | — |
| Collaboration | S1 stage 2 | 2 | — |
| Peak analysis | S2 §06 | 3 | R4 |
| Layered graphs | S2 R4 | 3 | R4 |
| Batch plotting | S2 R4 | 3 | R4 |
| Graph templates (10 starters) | S2 §11 | 3 | R4 |
| Publication figure designer | S2 §09 | 3 | R5 |
| Significance annotation | S2 §08 | 3 | R5 |
| Figure audit (12 checks) | S2 §12 | 3 | R5 |
| Reproducibility panel + Trace | S2 §13 | 3 | R5 |
| Journal figure presets | S2 §10 | 3 | R5 |
| Manuscript ↔ figure integration | S2 R5 | 3 | R5 |
| Full audit trail | S1 stage 3 | 3 | R5 |
| Journal formatting | S1 stage 3 | 3 | — |
| DOCX / PDF / LaTeX export | S1 API, stage 3 | 3 | R5 |
| Submission prep | S1 stage 3 | 3 | — |
| University accounts | S1 stage 4 | 4 | — |
| Research labs | S1 stage 4 | 4 | — |
| Supervisor dashboards | S1 stage 4 | 4 | — |
| Institutional repositories | S1 stage 4 | 4 | — |
| Admin | S1 stage 4 | 4 | — |

## 8.6 Critical path

Ordered by dependency, not by roadmap label:

```
1. Schema + auth + projects            (nothing exists without this)
2. Data upload + worksheet + columns   (no analysis without data)
3. Graph rendering + PNG/PDF export    (first visible output)
4. Writing engine + accept/edit/reject (the other half of the MVP promise)
5. statistical_analyses + transformations (ordered)   ← R3, and Trace depends on this
6. Statistics wizard + significance annotation       (marker ⇒ analysis link)
7. audit_logs + versions + attribution enforcement   ← R5, the product's moat
8. Pre-submission checker              (needs 5, 6, 7)
9. figures + figure_panels + publication designer
10. journal_presets (with source + date)
11. figure audit + reproducibility + Trace
12. Export Center (DOCX/PDF/LaTeX/PPTX)
13. references + literature
14. Collaboration
15. Institutions + roles + dashboards
```

Items 5 and 7 are the true critical path. `data_transformations` must be an ordered replayable log
from day one — retrofitting order into a flag-based design means rewriting the provenance chain
after every figure already exists. `audit_logs.attribution NOT NULL` must be in the initial schema
migration — retrofitting attribution means reconstructing history that was never recorded, which is
precisely the failure mode the product exists to prevent.
