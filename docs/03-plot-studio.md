# 03 — SCIX Plot Studio Specification

Derived from `scix-plot-studio.html` (internal draft v0.1), all 18 sections. Line references point
at that file.

**Module position (L915):** "Plot Studio sits between the Writing and Literature modules, feeding a
shared Research Integrity layer and Export Center."

---

## 3.0 Pipeline

```
Import → Organize → Analyze → Plot → Customize → Validate → Export
```

Seven stages (L391–399). This is the module's spine and should drive navigation state, progress
indication, and the wizard structure.

| Stage | Sections that fulfil it |
|-------|-------------------------|
| Import | §03 data workspace, §02 DATA menu |
| Organize | §03 columns, §02 DATA (Filter/Sort/Group/Merge/Normalize) |
| Analyze | §07 statistics wizard, §06 curve fitting, §02 ANALYSIS menu |
| Plot | §04 wizard, §02 PLOT menu, §11 templates |
| Customize | §05 graph editor, §06 peak analysis, §02 FORMAT menu |
| Validate | §12 figure audit, §10 journal presets, §13 reproducibility |
| Export | §02 EXPORT menu, §09 publication figure designer |

## 3.1 §01 Main interface — three-pane layout

**Sub (L406):** "A three-pane layout familiar to researchers already using scientific plotting
software, with a modern shell around it."

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SCIX   | Research Project: Nanomaterial Study              Save   Export     │  ← title bar
├──────────────────────────────────────────────────────────────────────────────┤
│ File  Data  Analysis  Plot  Statistics  Format  Journal  Validate  Help      │  ← menu bar
├──────────────┬───────────────────────────────────────────────┬───────────────┤
│  PROJECT     │                GRAPH CANVAS                   │   PROPERTIES  │
│  Data        │                                               │ Chart Type    │
│  Worksheets  │                                               │ X Axis        │
│  Analyses    │                                               │ Y Axis        │
│  Graphs      │                                               │ Error Bars    │
│  Tables      │                                               │ Regression    │
│  Templates   │                                               │ Legend        │
│              │                                               │ Fonts         │
│              │                                               │ Symbols       │
│              │                                               │ Dimensions    │
├──────────────┴───────────────────────────────────────────────┴───────────────┤
│ Dataset: Experiment_01.xlsx | Rows: 120 | Columns: 8 | Analysis: ANOVA       │  ← status bar
└──────────────────────────────────────────────────────────────────────────────┘
```

### Layout regions

| Region | Contents | Notes |
|--------|----------|-------|
| **Title bar** | Product mark, active project name, Save, Export | Project name is editable/contextual |
| **Menu bar** | File · Data · Analysis · Plot · Statistics · Format · Journal · Validate · Help | 9 items here vs the 5 menu cards in §02 — see Q1 |
| **Left pane — Project tree** | Data · Worksheets · Analyses · Graphs · Tables · Templates | Object-tree navigation |
| **Centre — Graph canvas** | The rendered figure | Primary work surface |
| **Right pane — Properties** | Chart Type · X Axis · Y Axis · Error Bars · Regression · Legend · Fonts · Symbols · Dimensions | Context-sensitive property inspector |
| **Status bar** | `Dataset: <file> \| Rows: <n> \| Columns: <n> \| Analysis: <name>` | Live provenance display |

The status bar is a small but important detail: it keeps the current dataset and analysis
permanently visible, which supports the Research Integrity goal at zero UI cost.

## 3.2 §02 Navigation map — five menus

Full item lists in [00-source-extract.md](./00-source-extract.md) §02. Summary of coverage:

| Menu | Item count | Coverage |
|------|-----------:|----------|
| DATA | 10 | import, table, worksheet, cleaning, transforms, filter/sort/group, merge, normalize, calculated columns, missing values |
| ANALYSIS | 12 | descriptive, t-test, ANOVA, multiple comparison, correlation, regression, nonlinear, dose-response, survival, ROC, time-series, multivariate, custom |
| PLOT | ~18 | gallery, XY/line/scatter, column/bar, grouped/stacked, box/violin/histogram, area/heatmap/contour, survival/ROC/calibration, spectra/kinetic |
| FORMAT | ~14 | axes/labels/fonts, symbols/lines, error bars/legends/grid, colors/panel layout, annotations/equations, significance, figure size |
| EXPORT | 4 groups | PNG·TIFF·JPEG, SVG·PDF·EPS, DOCX·PPTX, LaTeX |

### Graph type inventory (consolidated)

Collected from §02 PLOT, §04 Step 2 and §08 — the complete set named anywhere in S2:

XY · Line · Scatter · Column · Bar · Grouped · Stacked · Box · Violin · Histogram · Area ·
Heatmap · Contour · Survival · ROC · Calibration · Spectrum/Spectra · Kinetic · Dose Response

19 named types. Any implementation should treat this as the canonical v1 type registry.

## 3.3 §03 Origin-style data workspace

A spreadsheet environment (L476–496).

### Grid model
- Rows are indexed (`#`), columns are typed and named
- Columns carry metadata (see below)
- Multiple worksheets per dataset

### Per-column capabilities (L490–495)

| Property | Purpose |
|----------|---------|
| Column name | Display label |
| Unit | Physical unit string; feeds the figure audit unit check |
| Data type | Numeric / text / date / categorical |
| X/Y designation | Independent vs dependent variable |
| Replicate designation | Marks repeated measurements (drives error bars, mean±SD) |
| Group designation | Categorical grouping (drives ANOVA, grouped plots) |
| Error column | Associates an uncertainty column with this column |
| Formula | Derived column — computed, not entered |
| Metadata | Free-form annotations |

**Design note:** X/Y, Replicate, Group and Error are *roles*, not data types. A single numeric
column can simultaneously be a Y, a replicate-bearing column, and belong to group "Sample A".
These must be separate, composable fields on the column entity — see
[05-data-model.md](./05-data-model.md).

## 3.4 §04 Graph creation wizard — four steps

Triggered by "New Graph" (L501).

### Step 1 — Select data
- Dataset + Worksheet pickers
- X Variable, Y Variable, Error dropdowns
- Three option flags:
  - ☐ Include replicates
  - ☐ Normalize data
  - ☐ Include missing values

### Step 2 — Select graph
15 types in a gallery, grouped in the source into 5 rows × 3 columns:
`XY · Line · Scatter` / `Column · Grouped · Box Plot` / `Violin · Histogram · Heatmap` /
`Survival · ROC · Dose Response` / `Spectrum · Kinetics · Calibration`

### Step 3 — Statistical analysis
Radio list (L525–532):
`None` · `Descriptive statistics` · `t-test` · `One-way / Two-way ANOVA` · `Tukey` ·
`Correlation` · `Linear / Nonlinear regression` · `Custom`

### Step 4 — Formatting
> Opens the full Graph Editor with the chosen data, graph type and analysis already attached to
> the figure. (L536–539)

**Critical requirement:** the wizard is a *setup* flow, not a rendering flow. Steps 1–3 produce a
graph specification; step 4 hands it to the editor. No analysis runs without an explicit selection
in step 3 — this is the enforcement point for rule R3.

## 3.5 §05 Graph editor — "the strongest surface in the product"

Explicitly identified as the most important screen (L547).

### Left toolbar — drawing
```
Select · Move
Zoom · Pan · Crosshair
Text · Arrow · Line
Shape
Significance
Annotation
```

10 tools in 6 groups. Selection/navigation, view control, annotation primitives, statistical
annotation.

### Top toolbar — file lifecycle
```
Undo · Redo · Save
──────────────────
New Graph · Duplicate
Template
──────────────────
Fit · Zoom · Full Screen
──────────────────
Preview · Validate · Export
```

Undo/redo is non-negotiable in an editor of this class. `Duplicate` and `Template` are how figures
propagate across a manuscript. `Validate` is the figure audit entry point.

### Right panel — properties
```
Graph
  Width · Height
  Background · Border
  Panel layout

X / Y Axis
  Title · Units · Scale
  Min / Max
  Major / Minor interval

Series
  Symbol · Line · Size
  Error bar · Transparency

Legend · Annotations
Statistics
```

## 3.6 §06 Advanced plotting

### Curve fitting (L599–603)
| Family | Models |
|--------|--------|
| Polynomial | Linear, Polynomial (n-degree) |
| Exponential-family | Exponential, Logarithmic, Power |
| Peak-shaped | Gaussian, Lorentzian, Sigmoidal |
| User | Custom equation |

### Output required with every fit (L605–609)
| Output | Note |
|--------|------|
| Equation | Rendered form of the fitted model |
| R² | Goodness of fit |
| Adjusted R² | Penalised R² |
| Residuals | Residual plot |
| Confidence interval | On the fit and/or parameters |
| Parameter estimates | Coefficients |
| Standard error | Per parameter |
| p-value | Per parameter |

Nine outputs per fit. Every one is an audit record — required for the manuscript to be
defensible.

### Peak analysis (L613–618)
- Peak detection · Peak position
- Peak height · Peak area
- FWHM · Baseline
- Peak fitting

Stated relevance (L619): spectroscopy, chromatography, materials-science datasets.

## 3.7 §07 Prism-style statistics wizard

**Sub (L627):** "SCIX explains what a test does; the researcher decides whether it's the right one."

This is a pedagogical requirement, not a cosmetic one: the wizard must describe each test's
purpose and assumptions, and must not auto-select a test on the user's behalf.

### Entry point — data shape
`Column` · `Grouped` · `XY` · `Survival` · `Contingency`

The user's data shape determines which tests are offered. This is the wizard's routing logic.

### Analysis catalogue

| Category | Tests |
|----------|-------|
| **Descriptive** | Mean · Median · SD · SEM · CV · CI |
| **Comparison** | t-test · Paired t-test · ANOVA · Two-way ANOVA · Multiple comparisons |
| **Correlation** | Pearson · Spearman |
| **Regression** | Linear · Polynomial · Nonlinear |
| **Clinical** | ROC · Survival · Kaplan-Meier |

Also named elsewhere in S2: one-way ANOVA, Tukey (post-hoc), Multiple Comparison, Time-Series,
Multivariate, Custom Analysis, Dose-Response (from §02 ANALYSIS).

**Consolidated v1 test registry — 21 entries:**

Descriptive statistics · t-test · Paired t-test · One-way ANOVA · Two-way ANOVA · Tukey ·
Multiple comparisons · Pearson correlation · Spearman correlation · Linear regression ·
Polynomial regression · Nonlinear regression · Dose-response · Survival analysis · Kaplan-Meier ·
ROC analysis · Time-series · Multivariate · Chi-square / contingency · Custom analysis

## 3.8 §08 Significance annotation

**Sub (L662):** "Automatic placement of significance markers — derived only from the analysis
actually run."

```
          ***
       ─────────
   ●       ●

  Control   Treatment
```

### Marker vocabulary (L669)
`*` · `**` · `***` · `****` · `ns` · `p = 0.032` · `p < 0.001`

Note both star notation and explicit p-value rendering are supported — journals differ.

### Constraint (the important part)
Significance markers are a *rendering of an analysis result*, never an independent judgement. The
system must not be able to draw a bracket or a `*` without a backing record in
`statistical_analyses` whose p-value generated it. This is a direct implementation of rule R3 and
is what makes the Research Integrity claim true rather than aspirational.

## 3.9 §09 Publication figure designer

A dedicated mode (L674) for assembling submission-ready multi-panel figures.

### Figure size presets
`Single column` · `1.5 column` · `Double column` · `Custom`

Worked example: **Width 85 mm · Height 65 mm · DPI 600**

600 DPI is the near-universal journal requirement for raster figures; it should be the default.

### Typography controls
Font · Size · Bold · Italic · Superscript · Subscript · Scientific notation

### Multi-panel layout
```
┌──────────────┬──────────────┐
│     (a)      │      (b)     │
├──────────────┼──────────────┤
│     (c)      │      (d)     │
└──────────────┴──────────────┘
```

> Graphs are dragged into panels and aligned automatically. (L702)

Panels are auto-lettered `(a)`, `(b)`, `(c)`, `(d)`. Alignment is automatic — no manual nudging.

## 3.10 §10 Journal figure presets

**Sub (L710):** "Verified formatting profiles per target journal, with the source of each rule always
visible."

```
TARGET JOURNAL
[ Select Journal ]

Figure requirements
────────────────────
Width · Height · Resolution
File format · Font
Maximum panels · Color requirements
```

**Distinguishing requirement (L719):**
> The system shows the source and date of each journal requirement rather than silently assuming
> outdated rules.

Journal requirements change. Every preset rule must therefore carry:
- the **source** (journal author guidelines URL / document)
- the **date** the rule was verified
- ideally a staleness warning when the verification date is old

This is a trust feature: the researcher can see whether a rule is current. It also means journal
presets need an admin/update workflow, not just static seed data. See Q8.

## 3.11 §11 Graph templates

Ten starter templates (L727–737), all marked ★:

1. Materials Characterization
2. Photocatalytic Study
3. Biological Assay
4. Cell Viability
5. Dose Response
6. Kinetic Study
7. Survey Analysis
8. Engineering Experiment
9. Regression
10. Spectroscopy

**Property (L725):** "Reusable, discipline-independent starting points that researchers can
customize and save."

So templates are user-creatable and persistable — `graph_templates` is a first-class entity
(S2 L860), not a hardcoded list.

## 3.12 §12 Research figure audit

**Sub (L743):** "A pre-export checklist unique to SCIX — the first layer of the Research Integrity
system."

12 checks:

| # | Check | Category |
|---|-------|----------|
| 1 | Dataset connected | provenance |
| 2 | X-axis assigned | axes |
| 3 | Y-axis assigned | axes |
| 4 | Units specified | units |
| 5 | Error bars identified | uncertainty |
| 6 | Statistical method recorded | method |
| 7 | Statistical values calculated | method |
| 8 | Figure resolution acceptable | output quality |
| 9 | Axis labels present | axes |
| 10 | Legend present | readability |
| 11 | Figure number assigned | manuscript integration |
| 12 | *Y-axis unit has not been specified* ⚠ | **the demo failure state** |

Item 12 in the source is the example of a **failing** check — it shows the checklist is live, not
decorative. A figure failing item 12 would block or warn on export.

Item 6+7 together are the integrity pair: not only must a statistical method be named, its values
must actually have been computed.

## 3.13 §13 Reproducibility panel

**Sub (L765):** "Every figure carries its own provenance record, traceable back to the source
dataset."

```
FIGURE 03

Source:      Experiment_01.xlsx
Data:        Worksheet 2
Processing:  Normalization → Log transformation
Analysis:    One-way ANOVA
Post-hoc:    Tukey
Plot:        Grouped column
Error:       SD
Created:     SCIX Plot Studio
Version:     v1.4

[ Trace Figure → returns to the underlying dataset and analysis ]
```

### Provenance fields

| Field | Meaning |
|-------|---------|
| Source | The uploaded file |
| Data | Which worksheet inside it |
| Processing | Ordered chain of transformations applied |
| Analysis | Which statistical test |
| Post-hoc | Which post-hoc test, if any |
| Plot | Graph type |
| Error | Error-bar basis (SD / SEM / CI) |
| Created | Originating tool |
| Version | Tool version at creation |

### The Trace action
> "returns to the underlying dataset and analysis"

This is a **bidirectional provenance link** and is the hardest and most valuable thing in this
module. It requires that the transformation chain be stored as an ordered, replayable list — not a
flag. `data_transformations` (S2 L855) must be an ordered log, and `Trace` must be able to
reconstruct or at minimum navigate to every intermediate state.

Note the example: `Normalization → Log transformation` — a two-step chain. A single boolean
`normalized: true` would be insufficient.

## 3.14 §14 Universal discipline engine

Per-discipline plotting capabilities — 7 disciplines × 4–6 capabilities. Full table in
[07-disciplines-terminology.md](./07-disciplines-terminology.md) §7.2.

**Sub (L784):** "Plot Studio is not restricted to any one field."

Note the seven here are a *subset* of the seventeen in S1 — Plot Studio's discipline coverage and
the platform's discipline coverage are different lists. See Q3.

## 3.15 §15 Technical architecture

```
SCIX PLOT STUDIO
↓
FRONTEND LAYER — Next.js / React          [Data] [Graph] [UI]
↕
BACKEND LAYER — FastAPI / Python         [Analysis] [Export] [Validation]
↓
SCIENTIFIC ENGINE                         [NumPy] [Pandas] [SciPy] [Statsmodels] [SymPy]
↓
VISUALIZATION                             [Matplotlib] [Plotly]
↓
EXPORT ENGINE    [TIFF] [PNG] [SVG] [PDF] [EPS] [DOCX] [PPTX] [LaTeX]
```

**Boundary semantics:**
- Frontend ↔ Backend is bidirectional (`↕`) — interactive property editing
- Backend → engine, engine → visualization, visualization → export are one-way (`↓`): a strict
  pipeline where data flows down and rendered artefacts flow out
- **Plotly** is in the stack, which implies interactive/HTML rendering in the browser;
  **Matplotlib** implies server-side static rendering for export. The split point must be decided
  — see Q4.

## 3.16 §16 Database structure

19 entities and the project-rooted relationship tree. Analysed in
[05-data-model.md](./05-data-model.md).

## 3.17 §17 Differentiators — three pillars

| | Pillar | Body |
|---|--------|------|
| ① | **Origin-style plotting** | A powerful data → analysis → graph workflow for demanding scientific plots. |
| ② | **Prism-style statistics** | Statistics → visualization → significance → publication, in one continuous path. |
| ③ | **Research integrity** | Data → analysis → figure → manuscript, as a reproducible research record. |

**Stated significance (L892):** "the third of which moves SCIX beyond a graphing tool."

Pillars ① and ② are competitive-parity features (Origin and Prism already do them). Pillar ③ is
the claim to differentiation and is what the entire integrity layer in
[06-integrity-authorship.md](./06-integrity-authorship.md) implements.

## 3.18 §18 Final product architecture & roadmap

### Platform map
```
                          SCIX
              SCIENTIFIC RESEARCH PLATFORM
                              │
 ┌────────────────────────────┼────────────────────────────┐
WRITING                    PLOT STUDIO                 LITERATURE
 Human writing              Data workspace              References
 Grammar                    Statistics                  DOI
 Sentence structure         Regression / Graphing        PDF · Evidence Matrix
 │                            │                            │
 └──────────────┬─────────────┴─────────────┬──────────────┘
                │                           │
             RESEARCH                   JOURNAL
             INTEGRITY                 PREPARATION
        Audit trail                Formatting
        Reproducibility            Figure rules
        Version control            References
        Data traceability         Submission
                │                           │
                └─────────────┬─────────────┘
                              │
                         EXPORT CENTER
                    DOCX · PDF · LaTeX · PPTX
```

### Platform layers

| Layer | Responsibilities |
|-------|------------------|
| **Writing** | Human writing, grammar, sentence structure |
| **Plot Studio** | Data workspace, statistics, regression/graphing |
| **Literature** | References, DOI, PDF, evidence matrix |
| **Research Integrity** | Audit trail, reproducibility, version control, data traceability |
| **Journal Preparation** | Formatting, figure rules, references, submission |
| **Export Center** | DOCX · PDF · LaTeX · PPTX |

Note: **Evidence Matrix** (Literature) and **Data traceability** (Integrity) are named only in
this diagram and appear nowhere else in either source — see Q5.

### Five releases
See [08-roadmap.md](./08-roadmap.md) §8.2 for the release table and the merged sequencing plan.
