# 04 — Technical Architecture

Consolidated from both sources. S1 §Under the Hood (L375–415), S2 §15 (L818–843), S2 §18
(L913–970), S1 §API surface (L404–413).

---

## 4.1 Declared stack

The stack is stated twice, in two different groupings. Merging them:

| Layer | Technology | Named responsibilities |
|-------|-----------|------------------------|
| **Frontend** | Next.js / React | Manuscript editor · Data manager · Graph & Plot Studio · Dashboard |
| **Backend** | FastAPI | Writing Engine · Data Engine · Research Engine · Auth · Export |
| **Scientific engine** | Python | Pandas · NumPy · SciPy · Statsmodels · Matplotlib · Plotly · SymPy |
| **Data store** | PostgreSQL | 9 named tables (S1) / 19 named entities (S2) |

S1 sub-labels of the frontend: *Data · Graph · UI*
S2 sub-labels of the backend: *Analysis · Export · Validation*

**Library-to-responsibility mapping**

| Library | Implied use |
|---------|-------------|
| NumPy | array maths, numeric core |
| Pandas | dataframes, import, transforms, group-by |
| SciPy | statistical tests, distributions, curve fitting (`scipy.optimize`), signal processing for peak analysis |
| Statsmodels | ANOVA, regression, time-series, multiple-comparison post-hoc |
| SymPy | symbolic equations, custom curve-fit models, equation rendering |
| Matplotlib | server-side static figure rendering for export |
| Plotly | interactive in-browser figures |

SymPy's presence is a specific signal: it backs the **"Custom equation"** curve-fitting option
(S2 L602) and the **"Annotations · Equations"** formatting option (S2 L463), plus rendering fitted
equations symbolically rather than as float-formatted strings.

## 4.2 Layer model

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND — Next.js / React                             │
│  Manuscript Editor │ Data Manager │ Plot Studio │ Dash  │
└──────────────────────────┬──────────────────────────────┘
                           ↕  HTTPS / JSON (+ WebSocket for
                               long-running analysis jobs)
┌──────────────────────────┴──────────────────────────────┐
│  BACKEND — FastAPI                                      │
│  Writing Engine │ Data Engine │ Research Engine         │
│  Auth          │ Export                                 │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  SCIENTIFIC ENGINE — Python                             │
│  Pandas · NumPy · SciPy · Statsmodels · SymPy           │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  VISUALIZATION — Matplotlib · Plotly                     │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  EXPORT ENGINE                                          │
│  TIFF · PNG · SVG · PDF · EPS · DOCX · PPTX · LaTeX     │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  POSTGRESQL                                             │
└─────────────────────────────────────────────────────────┘
```

### Boundary semantics

| Boundary | Arrow | Implication |
|----------|-------|-------------|
| Frontend ↔ Backend | `↕` | Interactive property editing; property panel changes round-trip. Needs async job handling for slow analyses. |
| Backend → Scientific engine | `↓` | Business logic orchestrates the scientific engine |
| Scientific engine → Visualization | `↓` | Figures are rendered objects, then formatted |
| Visualization → Export | `↓` | Render output is serialised per format |
| Everything → PostgreSQL | `↓` | Persistence beneath the pipeline |

**Undecided (Q4):** the source does not say whether Plotly renders in-browser and Matplotlib
server-side, or whether one does both. The presence of both, plus the "Publish Figure" naming in
S1 L418, implies a dual path. Must be decided before building the canvas.

## 4.3 Backend engine decomposition

S1 names four backend responsibilities. Modelled as service boundaries:

| Engine | Owns | Endpoints implied |
|-------|------|-------------------|
| **Writing Engine** | grammar, sentence formation, register, paragraph, terminology, consistency, manuscript structure | `/api/manuscripts/*`, `/api/writing/*` |
| **Data Engine** | upload, parse, worksheets, columns, transforms, filter/sort/group/merge/normalize | `/api/data/*` |
| **Research Engine** | statistics, curve fitting, peak analysis, figure generation | `/api/statistics/*`, `/api/graphs/*` |
| **Auth** | users, sessions, institutional accounts (Stage 4) | `/api/auth/*` |
| **Export** | DOCX/PDF/LaTeX/PPTX/figure formats | `/api/export/*` |

## 4.4 Core API surface

The eight endpoints given in S1 L404–413, with request/response inference:

| Method | Path | Source comment | Likely payload |
|--------|------|----------------|----------------|
| `POST` | `/api/projects` | create a research project | name, discipline, optional template |
| `GET` | `/api/projects` | list a researcher's projects | — |
| `POST` | `/api/manuscripts` | start a manuscript | project_id, title, discipline, journal target |
| `POST` | `/api/data/upload` | attach a dataset | project_id, file (multipart) |
| `POST` | `/api/statistics/analyze` | run a chosen statistical test | test name, data refs, parameters — **test is mandatory** |
| `POST` | `/api/graphs/create` | generate a figure from data | dataset/worksheet/columns, graph type, analysis ref |
| `POST` | `/api/references` | manage citations | user-supplied citation metadata only |
| `POST` | `/api/export/docx` | export to DOCX / PDF / LaTeX | manuscript/figure id, target format, journal preset |

**Observation:** the source labels this the "CORE API surface" — an 8-endpoint skeleton, not a
complete contract. The full endpoint set required by the feature set is far larger; see
§4.8 below for the derived expansion.

## 4.5 Derived API expansion

Not in the source — derived from the features in [02](./02-writing-module.md) and
[03](./03-plot-studio.md). Provided as an engineering starting point.

### Projects & manuscripts
```
POST   /api/projects                    GET    /api/projects
GET    /api/projects/{id}               PATCH  /api/projects/{id}
DELETE /api/projects/{id}
POST   /api/manuscripts                 GET    /api/manuscripts/{id}
GET    /api/manuscripts/{id}/sections   PATCH  /api/manuscripts/{id}/sections/{sid}
POST   /api/manuscripts/{id}/sections
GET    /api/manuscripts/{id}/revisions          # version history
POST   /api/manuscripts/{id}/check               # 5-dimension pre-submission checker
GET    /api/manuscripts/{id}/check/{runId}
```

### Writing
```
POST   /api/writing/grammar             # tool 01
POST   /api/writing/sentences           # tool 02
POST   /api/writing/register            # tool 03
POST   /api/writing/paragraph           # tool 04
POST   /api/writing/terminology         # tool 05
POST   /api/writing/consistency         # tool 06 — detect variant groups
POST   /api/writing/consistency/apply   # apply chosen canonical variant doc-wide
POST   /api/writing/suggestions/{id}/accept
POST   /api/writing/suggestions/{id}/edit
POST   /api/writing/suggestions/{id}/reject
GET    /api/writing/rejections          # dismissed suggestions
```

### Data
```
POST   /api/data/upload                 GET    /api/datasets
GET    /api/datasets/{id}               GET    /api/datasets/{id}/worksheets
GET    /api/worksheets/{id}             PATCH  /api/columns/{id}
POST   /api/data/transformations        # ordered, replayable
POST   /api/data/filter                 POST   /api/data/sort
POST   /api/data/group                  POST   /api/data/merge
POST   /api/data/normalize              POST   /api/data/calculate-column
GET    /api/datasets/{id}/provenance
```

### Statistics & figures
```
POST   /api/statistics/analyze          # test name REQUIRED
GET    /api/statistics/analyses/{id}    # full result record
POST   /api/statistics/analyses/{id}/posthoc
POST   /api/graphs/create               GET    /api/graphs
GET    /api/graphs/{id}                 PATCH  /api/graphs/{id}
DELETE /api/graphs/{id}
POST   /api/graphs/{id}/duplicate       POST   /api/graphs/{id}/templates
POST   /api/graphs/{id}/render          # returns a render spec / image
POST   /api/graphs/{id}/fit             # curve fitting
POST   /api/graphs/{id}/peaks           # peak analysis
POST   /api/graphs/{id}/significance    # markers from a backing analysis
POST   /api/figures                     # publication figure (multi-panel)
POST   /api/figures/{id}/panels         PATCH  /api/figures/{id}/panels/{pid}
```

### Validation, integrity, export
```
POST   /api/graphs/{id}/audit           # §12 — 12 checks
POST   /api/figures/{id}/reproducibility  # §13 provenance record
POST   /api/figures/{id}/trace          # §13 — back to dataset + analysis
GET    /api/journal-presets             POST   /api/journal-presets/{id}/verify
POST   /api/export/docx                 POST   /api/export/pdf
POST   /api/export/latex                POST   /api/export/figure
GET    /api/audit/log                   # audit trail
```

## 4.6 Platform layer architecture

From S2 §18. Six layers, three of which are cross-cutting:

| Layer | Status in sources | Owns |
|-------|-------------------|------|
| **Writing** | Detailed (S1 §Writing) | Human writing, grammar, sentence structure |
| **Plot Studio** | Detailed (S2, 18 sections) | Data workspace, statistics, regression/graphing |
| **Literature** | Named only | References, DOI, PDF, Evidence Matrix |
| **Research Integrity** | Named in diagram; requirements in S1 authorship + S2 §12/§13 | Audit trail, reproducibility, version control, data traceability |
| **Journal Preparation** | Named in diagram; partially in S2 §10 | Formatting, figure rules, references, submission |
| **Export Center** | Named in diagram | DOCX · PDF · LaTeX · PPTX |

**Architecture rule implied by the diagram:** Writing, Plot Studio and Literature are *sibling*
modules that all feed *downward* into Research Integrity and Journal Preparation, which converge
into Export Center. Integrity is not a feature of each module — it is a shared substrate. Therefore
`audit_logs`, `versions` and provenance must be written by all three modules through one shared
mechanism, not three separate ones.

## 4.7 Cross-cutting concerns

Not specified in the sources, but required by the stated feature set:

| Concern | Requirement source | Notes |
|---------|-------------------|-------|
| **Async job execution** | Curve fitting, multivariate, large-dataset analysis | The frontend↔backend link is `↕` and analyses can be slow. Needs a job queue + progress; Plotly/WebSocket or polling. |
| **File/object storage** | `/api/data/upload`; §13 source file names | Datasets are files (`.xlsx`). PostgreSQL is not a file store — needs S3/local object storage with a DB pointer. |
| **AuthN/AuthZ** | `users` entity; Stage 4 university accounts | Row-level project ownership from day one; institutional tenancy is Stage 4. |
| **Versioning** | `versions` entity; "version control" (Stage 2) | Manuscript revisions (S1: `manuscripts → sections, revisions`) and figure versions both need it. |
| **Discipline profile registry** | "per discipline" (S1 L421, L301) | Data-driven, seeded, extensible. |
| **Journal preset registry** | §10 | Must carry source + verification date per rule. |
| **Rendering determinism** | §13 provenance, journal specs | Same figure + version → same output. Requires pinning library versions. |
| **Rate/size limits** | upload, analysis | Not specified. See Q9. |

## 4.8 Deployment shape

Not specified. The sources imply at minimum:

- A stateless API tier (FastAPI) — required for Stage 4 institutional scale
- A worker tier for the scientific engine and export engine — they are CPU-bound and slow
- PostgreSQL
- Object storage for datasets and rendered figures
- Optional: separate rendering service for Matplotlib (headless), since server-side plotting needs
  a non-interactive matplotlib backend and specific fonts for journal compliance

The frontend is Next.js, which can be statically exported or served by the API tier.

## 4.9 Naming conventions observed in the sources

| Thing | Convention | Example |
|-------|-----------|---------|
| DB entities | `snake_case`, singular or plural as listed | `graph_series`, `journal_presets` (mixed — see Q6) |
| API paths | `snake_case`, plural nouns, `/api/` prefix | `/api/statistics/analyze` |
| Menu commands | Title Case | `Import Data`, `Calculate Column` |
| Menu groups | ALL CAPS | `DATA`, `ANALYSIS`, `PLOT`, `FORMAT`, `EXPORT` |
| Writing tool tags | `NN · CAPS` | `01 · GRAMMAR` |
| Plot Studio sections | two-digit + Title Case | `01 Main interface` |
| Releases | `RELEASE N — CAPS` | `RELEASE 3 — PRISM-STYLE` |
| Stages | `STAGE N — CAPS` | `STAGE 2 — RESEARCH PLATFORM` |
| Discipline names | Title Case, shared across both sources | `Materials Science`, `Computer Science` |
| Library names | as vendor writes them | `FastAPI`, `Next.js`, `NumPy`, `SciPy`, `Statsmodels`, `SymPy`, `Plotly`, `Matplotlib`, `Pandas` |
