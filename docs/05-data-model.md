# 05 — Data Model

Consolidated PostgreSQL entity set from both sources.

- **S1 L398–400** — 9 table groups (product-level)
- **S2 L852–863** — 19 entities (module-level, detailed)
- **S2 L866–884** — relationship tree

---

## 5.1 Entity inventory and cross-source mapping

S1 names 9; S2 names 19. They are **not** in conflict — S2 is a superset. S2 adds the
decomposition of S1's coarse names.

| S2 entity | S1 counterpart | Layer | Notes |
|-----------|----------------|-------|-------|
| `users` | `users` | Auth | |
| `projects` | `projects` | Core | **Root of every record** (S2 L849) |
| `datasets` | `datasets` | Data | |
| `worksheets` | — | Data | S1 has no worksheet concept; S2 §03 requires it |
| `columns` | — | Data | Column metadata: name, unit, type, roles |
| `data_transformations` | — | Data | Ordered, replayable chain (§13 Trace) |
| `statistical_analyses` | `analyses` | Research | |
| `analysis_parameters` | — | Research | |
| `graphs` | — | Plot | |
| `graph_series` | — | Plot | |
| `graph_axes` | — | Plot | |
| `graph_annotations` | — | Plot | Includes significance markers |
| `graph_templates` | — | Plot | |
| `figures` | `figures` | Plot | Publication figures |
| `figure_panels` | — | Plot | |
| `journal_presets` | `journal_settings` | Journal | Note the name difference — see Q6 |
| `exports` | — | Export | |
| `audit_logs` | — | Integrity | |
| `versions` | `revisions` | Integrity | S1: `manuscripts → sections, revisions` |

### S1 entities with no S2 counterpart

S1 L399–400 also names: `manuscripts`, `sections`, `revisions`, `tables`, `references`.

| S1 entity | S2 counterpart | Notes |
|-----------|----------------|-------|
| `manuscripts` | — | **Absent from S2 entirely.** The Writing module's storage model is unspecified. Major gap — Q10. |
| `sections` | — | Same gap |
| `revisions` | `versions` | Probably the same concept under a different name |
| `tables` | — | Absent from S2. A table entity is needed (manuscript checker has 4 table checks). Minor gap. |
| `references` | — | Absent from S2, though Literature is a named platform layer and `/api/references` is a named endpoint. Major gap — Q10. |

**Conclusion:** the union of both sources is **24 entities**. S2's 19 is a Plot-Studio-scoped
schema; S1's platform-level schema adds 5 more that S2 never modelled. Both are required.

## 5.2 Relationship tree (S2 verbatim, L866–884)

```
PROJECT
  ├── DATASET
  │     └── WORKSHEET
  │           └── COLUMNS
  │
  ├── ANALYSIS
  │     └── RESULTS
  │
  ├── GRAPH
  │     ├── SERIES
  │     ├── AXES
  │     └── ANNOTATIONS
  │
  └── FIGURE
        ├── PANEL A
        ├── PANEL B
        ├── PANEL C
        └── PANEL D
```

Read as: `project` is the aggregate root; `dataset` is 1:N under project; `worksheet` is 1:N under
dataset; `columns` is 1:N under worksheet. `graphs` and `figures` are siblings hanging directly off
project, with their own children.

**Not drawn but required by the features:**

```
PROJECT
  └── MANUSCRIPT
        ├── SECTIONS
        ├── REVISIONS
        ├── FIGURES (referenced)
        ├── TABLES
        └── REFERENCES
```

Figures must be linkable *from* a manuscript even though the tree shows them only under project.

## 5.3 Entity specifications

Field lists below are derived from the feature requirements in [02](./02-writing-module.md),
[03](./03-plot-studio.md) and [06](./06-integrity-authorship.md). The source names the entities and
their roles but does not give column definitions.

### `users`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| email | citext unique | |
| name | text | |
| institution_id | fk → institutions | Stage 4; nullable at MVP |
| role | enum | `researcher`, `supervisor`, `admin` (Stage 4) |
| created_at | timestamptz | |

### `projects`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| owner_id | fk → users | |
| name | text | Title bar shows "Research Project: Nanomaterial Study" |
| discipline | fk → discipline_profiles | Drives terminology, templates, stat methods, journal formats |
| target_journal_id | fk → journal_presets | nullable |
| created_at / updated_at | timestamptz | |

### `datasets`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| project_id | fk → projects | |
| source_filename | text | §13 shows `Experiment_01.xlsx` |
| storage_key | text | Object-storage pointer |
| row_count / column_count | int | Status bar shows `Rows: 120 \| Columns: 8` |
| import_hash | text | Provenance + duplicate detection |
| imported_at | timestamptz | |

### `worksheets`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| dataset_id | fk → datasets | |
| name | text | "Worksheet 1", "Worksheet 2" |
| row_count | int | |

### `columns`
The richest metadata entity. From §03 (L490–495):

| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| worksheet_id | fk → worksheets | |
| ordinal | int | Grid position |
| name | text | Column name |
| unit | text | Feeds §12 audit check "Units specified" |
| data_type | enum | numeric, text, date, categorical |
| role_x | bool | X designation |
| role_y | bool | Y designation |
| is_replicate | bool | Replicate designation |
| group_name | text | Group designation |
| error_column_id | fk → columns (self) | Error column |
| formula | text | Formula for derived column |
| metadata | jsonb | Free-form |

**Key design point:** X/Y, replicate and group are *independent boolean/enum roles*, not a single
enum. A numeric column can be Y **and** a replicate-bearing column **and** in group "Sample A".
Compressing these into one column type will break the wizard's Step-1 dropdowns.

Data values themselves: at volume, use a columnar/array store rather than one row per cell. Not
specified in the source — Q11.

### `data_transformations`
**Must be an ordered, replayable log.** §13's `Processing: Normalization → Log transformation`
requires a chain, and the `Trace Figure` action requires replay.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| worksheet_id | fk → worksheets | |
| seq | int | **Ordering is essential** |
| transform_type | enum | normalize, log, filter, sort, group, merge, calculate_column, missing_values |
| params | jsonb | Transform arguments |
| input_columns / output_columns | fk[] | |
| created_by | fk → users | |
| created_at | timestamptz | |

### `statistical_analyses`
The integrity-critical entity. Every figure, annotation and reported p-value traces here.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| project_id | fk → projects | |
| worksheet_id | fk → worksheets | |
| test_name | enum | The 21-test registry (see §5.5) |
| library | text | scipy / statsmodels / sklearn — for reproducibility |
| library_version | text | **Required for reproducibility** |
| inputs | jsonb | Column references, group structure |
| results | jsonb | Full result payload |
| posthoc_test | enum | nullable — e.g. Tukey |
| significance_level | numeric | default 0.05 |
| selected_by | fk → users | The researcher chose this (rule R3) |
| created_at | timestamptz | |

### `analysis_parameters`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| analysis_id | fk → statistical_analyses | |
| name | text | e.g. `n`, `df`, `confidence` |
| value | text | |
| label | text | e.g. `t(28) = 2.045, p = 0.032` |

Supports the §06 "Displayed with every fit" outputs: parameter estimates, standard error, p-value.

### `graphs`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| project_id | fk → projects | |
| graph_type | enum | The 19-type registry (§5.6) |
| width / height | numeric | mm |
| dpi | int | default 600 |
| background / border | | |
| panel_layout | jsonb | |
| source_analysis_id | fk → statistical_analyses | nullable |
| created_by / created_at | | |

### `graph_series`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| graph_id | fk → graphs | |
| name | text | Series label |
| x_column_id / y_column_id | fk → columns | |
| error_column_id | fk → columns | Error bars |
| error_basis | enum | SD / SEM / CI |
| symbol / line_style / size / color / transparency | | Right-panel Series group |

### `graph_axes`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| graph_id | fk → graphs | |
| axis | enum | x, y |
| title | text | |
| unit | text | Feeds §12 "Y-axis unit" check |
| scale | enum | linear, log, loglog, semilog, categorical |
| min / max | numeric | |
| major_interval / minor_interval | numeric | |
| label_present | bool | §12 audit check 9 |

### `graph_annotations`
Includes both free annotations and significance markers — both live on the canvas.

| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| graph_id | fk → graphs | |
| kind | enum | text, arrow, line, shape, significance |
| content | text | |
| x / y / position | | Canvas coordinates |
| style | jsonb | font, size, bold, italic, superscript, subscript |
| **source_analysis_id** | fk → statistical_analyses | **Required when kind = significance** |
| marker | text | `*`, `**`, `***`, `****`, `ns`, `p = 0.032`, `p < 0.001` |

**Invariant:** `kind = 'significance'` requires a non-null `source_analysis_id`, and the marker must
equal that analysis's p-value rendered. Enforce with a DB check constraint. This is what makes
§08's "derived only from the analysis actually run" true.

### `graph_templates`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| project_id | fk → projects, **nullable** | null = system template |
| name | text | The 10 named starters |
| discipline | text | nullable |
| graph_spec | jsonb | Full graph + series + axes spec |
| is_system | bool | ★-marked starters |
| created_by / created_at | | |

### `figures` and `figure_panels`
Publication figures (multi-panel), §09.

`figures`:
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| project_id | fk → projects | |
| figure_number | text | §12 audit check 11 |
| size_preset | enum | single_column, one_point_five_column, double_column, custom |
| width_mm / height_mm / dpi | | Worked example: 85 × 65 mm @ 600 |
| journal_preset_id | fk → journal_presets | |
| caption | text | |
| provenance | jsonb | §13 record — or derive it |
| created_at | timestamptz | |

`figure_panels`:
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| figure_id | fk → figures | |
| panel_label | text | `(a)`, `(b)`, `(c)`, `(d)` |
| graph_id | fk → graphs | Graphs dragged into panels |
| grid_row / grid_col | int | Auto-alignment |
| ordinal | int | Auto-lettering order |

### `journal_presets`
**Must carry source and verification date per rule** — §10 (L719).

| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| journal_name | text | |
| **rule_source** | text | **URL or document** — mandatory |
| **rule_verified_at** | date | **mandatory** |
| max_panels | int | |
| color_requirements | text | e.g. "CMYK only", "colour-blind safe" |
| width_mm / height_mm / resolution / file_format / font | | |
| stale_after_days | int | Trigger a staleness warning |

### `exports`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| project_id | fk → projects | |
| target_type | enum | manuscript, figure, table |
| target_id | uuid | |
| format | enum | docx, pdf, latex, pptx, png, tiff, jpeg, svg, eps |
| storage_key | text | |
| journal_preset_id | fk → journal_presets | |
| created_by / created_at | | |

### `audit_logs`
The integrity backbone. Written by **all** modules (see [04](./04-architecture.md) §4.6).

| Field | Type | Notes |
|-------|------|-------|
| id | bigserial PK | Append-only |
| project_id | fk → projects | |
| actor_type | enum | `human`, `software` — the authorship badge value |
| actor_user_id | fk → users, nullable | null when actor is software |
| actor_component | text | `grammar`, `consistency`, `plotly`, `matplotlib` |
| action | text | `edit_accepted`, `figure_exported`, `analysis_run` |
| target_type / target_id | | |
| before_value / after_value | jsonb | The actual diff |
| **attribution** | enum | **denormalised copy of actor_type — mandatory** |
| created_at | timestamptz | Never updated, never deleted |

**Invariant:** every row has a non-null `attribution`. No row may exist without it. This is rule R5
enforced at the storage layer.

### `versions`
| Field | Type | Notes |
|-------|------|-------|
| id | uuid PK | |
| project_id | fk → projects | |
| scope | enum | manuscript, section, graph, figure, dataset |
| scope_id | uuid | |
| version_no | int | |
| snapshot | jsonb | |
| author_type | enum | `human`, `software` |
| author_user_id | fk → users, nullable | |
| parent_version_id | fk → versions | Branch-free linear history |
| message | text | |
| created_at | timestamptz | |

### Entities required but absent from both sources

Needed to build the stated features. Each maps to an open question in
[10-open-questions.md](./10-open-questions.md).

| Entity | Required by | Status |
|--------|--------------|--------|
| `manuscripts` | S1 names it; `/api/manuscripts` endpoint; entire Writing module | **Absent from S2** — Q10 |
| `sections` | S1 `manuscripts → sections`; §Structure checker | Absent from S2 — Q10 |
| `manuscript_revisions` | S1 `revisions` | Absent from S2 — Q10 |
| `references` | Literature layer; `/api/references`; §REFERENCES checker | Absent from S2 — Q10 |
| `tables` | S1 names it; §TABLES checker (4 checks) | Absent from S2 |
| `discipline_profiles` | "per discipline" terminology/templates/stats/journals | Absent from both |
| `terminology_rules` | Terminology checker, consistency checker | Absent from both |
| `suggestions` | Accept/Edit/Reject workflow (R6) | Absent from both |
| `suggestion_rejections` | Persistent dismissals | Absent from both |
| `institutions` | Stage 4 university accounts | Absent from both |
| `figure_audits` | §12 audit results over time | Absent from both |
| `column_values` | Actual cell data | Not modelled — Q11 |

## 5.4 Referential integrity rules

| Rule | Reason |
|------|--------|
| `audit_logs.attribution` NOT NULL | R5 |
| `graph_annotations.source_analysis_id` NOT NULL when `kind='significance'` | §08 |
| `journal_presets.rule_source` and `rule_verified_at` NOT NULL | §10 |
| `statistical_analyses.selected_by` NOT NULL | R3 |
| `statistical_analyses.library_version` NOT NULL | §13 reproducibility |
| `versions.author_type` NOT NULL | R5 |
| ON DELETE RESTRICT from `projects` to `audit_logs` | Append-only audit trail must survive project deletion attempts |
| ON DELETE CASCADE within a project subtree | Deleting a worksheet removes its columns |

## 5.5 Statistical test registry

Consolidated from §02 ANALYSIS, §04 Step 3, §07. 21 tests — the `statistical_analyses.test_name`
enum:

| # | Test | Category |
|---|------|----------|
| 1 | Descriptive statistics | Descriptive |
| 2 | t-test | Comparison |
| 3 | Paired t-test | Comparison |
| 4 | One-way ANOVA | Comparison |
| 5 | Two-way ANOVA | Comparison |
| 6 | Tukey | Post-hoc |
| 7 | Multiple comparisons | Comparison |
| 8 | Pearson correlation | Correlation |
| 9 | Spearman correlation | Correlation |
| 10 | Linear regression | Regression |
| 11 | Polynomial regression | Regression |
| 12 | Nonlinear regression | Regression |
| 13 | Dose-response | Dose |
| 14 | Survival analysis | Clinical |
| 15 | Kaplan-Meier | Clinical |
| 16 | ROC analysis | Clinical |
| 17 | Time-series | Time |
| 18 | Multivariate | Multivariate |
| 19 | Chi-square / contingency | Categorical |
| 20 | Curve fit (9 model families) | Regression |
| 21 | Custom analysis | Custom |

## 5.6 Graph type registry

Consolidated from §02 PLOT, §04 Step 2. 19 types — the `graphs.graph_type` enum:

`XY` · `Line` · `Scatter` · `Column` · `Bar` · `Grouped` · `Stacked` · `Box` · `Violin` ·
`Histogram` · `Area` · `Heatmap` · `Contour` · `Survival` · `ROC` · `Calibration` · `Spectrum` ·
`Kinetic` · `Dose-response`

Curve-fit model registry (§06, 9 entries) — a separate enum:
`Linear` · `Polynomial` · `Exponential` · `Logarithmic` · `Power` · `Gaussian` · `Lorentzian` ·
`Sigmoidal` · `Custom`
