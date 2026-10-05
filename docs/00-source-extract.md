# 00 — Source Extract (Verbatim)

Everything textual in the two source HTML files, reproduced verbatim and grouped by section.
No paraphrasing, no summarising, no interpretation. This document exists so that every derived
document in this folder can be traced back to an exact source line.

Line references point at the original HTML files in the repository root.

---

# SOURCE S1 — `nm-scientific-research-studio.html`

**Title (L6):** NM Scientific Research Studio
**Brand (L227):** `NM SCIENTIFIC RESEARCH STUDIO` (with "SCIENTIFIC" in red)
**Footer (L483):** `NM SCIENTIFIC RESEARCH STUDIO — PRODUCT CONCEPT — HUMAN-CENTERED SCIENTIFIC WRITING`

## Navigation (L228–235)

| Label | Anchor |
|-------|--------|
| Writing | `#writing` |
| Authorship | `#authorship` |
| Architecture | `#architecture` |
| Disciplines | `#disciplines` |
| Roadmap | `#roadmap` |

## Hero (L238–262)

**Eyebrow (L240):** `HUMAN-WRITTEN · SCIENTIFICALLY ORGANIZED · PUBLICATION READY`

**Headline (L241):**
> Your research, *written correctly* — never rewritten for you

**Dek (L242):**
> A scientific writing and research platform that improves grammar, structure, terminology and
> formatting — without inventing a single scientific claim.

### The worked example card (L244–258)

```
ORIGINAL — WRITTEN BY THE RESEARCHER
The material is [showing] very high activity because it is [having] good surface area.

SUGGESTED REVISION — LANGUAGE ONLY
The material [exhibited] high activity, [which may be associated with its large surface area].

[ Accept ]  [ Edit ]  [ Reject ]
```

`showing` and `having` are struck through in manuscript-red (deletions).
`exhibited` and `which may be associated with its large surface area` are highlighted in green
(insertions). Actions: **Accept**, **Edit**, **Reject**.

**Hero note (L260):**
> **Core principle:** the researcher provides the ideas, data, interpretation and scientific
> content. The software corrects language, structure, formatting and presentation without
> inventing scientific information.

## Product identity band (L264–269)

> Not an **AI paper-writing service** (green). A **scientific writing and publication** platform (blue).

*PRODUCT IDENTITY — NM SCIENTIFIC RESEARCH STUDIO*

## § Language & Writing Module (L271–318)

**Eyebrow:** `LANGUAGE & WRITING MODULE`
**Heading:** Every layer of language, checked — none of the science, touched
**Dek:** From single-word grammar fixes to full-manuscript consistency, each tool acts only on how
something is said, never on what it claims.

### Six feature cards (L277–308)

| Tag | Title | Body |
|-----|-------|------|
| `01 · GRAMMAR` | Grammar correction | Tense, subject–verb agreement, articles, prepositions, plurals, pronouns, punctuation, spelling, capitalization, fragments, run-ons. |
| `02 · SENTENCES` | Sentence formation | Rough, non-native phrasing rebuilt into correct scientific English — the researcher approves every change. |
| `03 · REGISTER` | Scientific language improvement | Academic English, concise or formal phrasing, active/passive voice, readability, redundancy, flow — as selectable options. |
| `04 · PARAGRAPH` | Paragraph-level checking | Topic sentences, sequencing, repetition, transitions, coherence, sentence length, terminology consistency within a paragraph. |
| `05 · TERMINOLOGY` | Scientific terminology checker | "nano particle" → nanoparticle, "bio sensor" → biosensor — plus units, formulas, gene/protein notation, math notation, per discipline. |
| `06 · CONSISTENCY` | Consistency checker | Catches CeNiO₃ vs CeNiO3, UV-Vis vs UV–Vis, Fig. 1 vs Figure 1 — then applies one chosen style throughout. |

### Consistency checker examples (L310–316)

| Wrong | Right |
|-------|-------|
| `CeNiO3` | `CeNiO₃` |
| `UV-Vis` | `UV–Vis` |
| `10mg` | `10 mg` |
| `Fig. 1` | `Figure 1` |

## § Pre-submission (L320–348)

**Eyebrow:** `PRE-SUBMISSION`
**Heading:** One manuscript checker, five dimensions
**Dek:** Run before submission — language, structure, references, figures and tables, all checked
in the same pass.

| Dimension | Checks |
|-----------|--------|
| **LANGUAGE** | Grammar · Spelling · Sentence formation · Academic style · Terminology |
| **STRUCTURE** | Heading hierarchy · Abstract · Keywords · Intro / Methods · Results / Discussion · Conclusion |
| **REFERENCES** | Missing citations · Duplicate references · Unused references · Citation numbering · Reference style |
| **FIGURES** | Figure numbering · Captions · In-text references · Resolution · Axis labels & units |
| **TABLES** | Table numbering · Captions · Units · In-text references |

All items are rendered with a ✓ prefix in the source.

## § The Differentiator (L350–373)

**Eyebrow:** `THE DIFFERENTIATOR`
**Heading:** A visible line between what the researcher wrote and what the software touched
**Dek:** Every change is labeled at the moment it happens — not disclosed after the fact. This is
what separates a writing assistant from an AI humanizer.

### SCIX AUTHORSHIP POLICY panel (L356–371)

Status indicator: `● HUMAN AUTHORSHIP MODE — ENABLED`

| Item | Attribution |
|------|-------------|
| Research content | 🟢 HUMAN |
| Research interpretation | 🟢 HUMAN |
| Experimental results | 🟢 HUMAN |
| Grammar correction | 🔵 SOFTWARE |
| Spelling correction | 🔵 SOFTWARE |
| Formatting | 🔵 SOFTWARE |
| Statistical calculation | 🔵 SOFTWARE |
| Figure generation from user data | 🔵 SOFTWARE |

*(HUMAN badges are green-tinted `#8be5ac`; SOFTWARE badges are blue-tinted `#9db9ff`; the panel
background is the dark ink colour `#1c1c1a` with paper-coloured text.)*

## § Under the Hood (L375–415)

**Eyebrow:** `UNDER THE HOOD`
**Heading:** Built as a research platform, not a text box
**Dek:** A Next.js interface over a FastAPI backend, with a dedicated scientific computing engine
and a PostgreSQL project model underneath.

### Layer stack (L381–401)

```
Frontend — Next.js / React
  [Manuscript editor] [Data manager] [Graph & Plot Studio] [Dashboard]
        ↕
Backend — FastAPI
  [Writing Engine] [Data Engine] [Research Engine] [Auth · Export]
        ↓
Scientific engine — Python
  [Pandas] [NumPy] [SciPy] [Statsmodels] [Matplotlib] [Plotly] [SymPy]
        ↓
PostgreSQL
  [users] [projects] [manuscripts → sections, revisions] [datasets] [analyses]
  [figures] [tables] [references] [journal_settings]
```

### Core API surface (L404–413)

| Method | Path | Comment |
|--------|------|---------|
| `POST` | `/api/projects` | create a research project |
| `GET` | `/api/projects` | list a researcher's projects |
| `POST` | `/api/manuscripts` | start a manuscript |
| `POST` | `/api/data/upload` | attach a dataset |
| `POST` | `/api/statistics/analyze` | run a chosen statistical test |
| `POST` | `/api/graphs/create` | generate a figure from data |
| `POST` | `/api/references` | manage citations |
| `POST` | `/api/export/docx` | export to DOCX / PDF / LaTeX |

## § One Core, Every Field (L417–431)

**Eyebrow:** `ONE CORE, EVERY FIELD`
**Heading:** Not chemistry software. Not biology software.
**Dek:** Each discipline carries its own terminology, manuscript templates, statistical methods,
and journal formats — on the same shared SCIX core.

**Disciplines (L422–429), 17 total:**

Chemistry · Physics · Biology · Biotechnology · Medicine · Pharmacy · Agriculture · Engineering ·
Computer Science · AI / Data Science · Mathematics · Environmental Science · Psychology ·
Economics · Management · Education · Social Sciences · Humanities

## § How It Gets Built (L433–460)

**Eyebrow:** `HOW IT GETS BUILT`
**Heading:** Four stages — starting with a working MVP, not the whole platform

| Stage | Title | Body |
|-------|-------|------|
| `STAGE 1 — MVP` | Prove the workflow | Editor, projects, grammar & sentence correction, data upload, basic graphs and tables. |
| `STAGE 2 — RESEARCH PLATFORM` | Add depth | Statistics, references, literature management, version control, collaboration. |
| `STAGE 3 — PUBLICATION PLATFORM` | Get to submission | Journal formatting, DOCX/PDF/LaTeX export, submission prep, research-integrity checks. |
| `STAGE 4 — INSTITUTIONAL PLATFORM` | Scale to labs | University accounts, research labs, supervisor dashboards, institutional repositories, admin. |

## § Closing — product identity as rules (L462–480)

**Heading:** A clear product identity, stated as rules

### YES (green)

- Grammar correction
- Sentence formation
- Academic English improvement
- Scientific terminology correction
- Spelling
- Data analysis, graphs, statistics
- References & formatting
- Journal preparation

### NO (red)

- AI-generated research claims
- AI-generated experimental results
- AI-generated references
- Automatic scientific content generation

---

# SOURCE S2 — `scix-plot-studio.html`

**Title (L6):** SCIX Plot Studio — Product Specification
**TOC brand (L356):** `SCIX PLOT STUDIO`
**TOC title (L362):** `Product Spec`
**TOC foot (L379–381):**
> NM GROUP OF INDUSTRIES
> & RESEARCH FOUNDATION
> Internal draft — v0.1

**Footer (L976):**
> SCIX PLOT STUDIO — INTERNAL PRODUCT SPECIFICATION — PREPARED FOR SOFTWARE DEVELOPMENT PLANNING

## Hero (L387–401)

**Eyebrow:** `SCIX / PLOT STUDIO MODULE`
**Heading (L389):** Scientific graphing, statistics & publication figures, in one workspace

**Dek (L390):**
> A major SCIX module combining Origin-style scientific plotting, Prism-style statistical
> workflow, and a discipline-independent research environment — built around a single working
> principle.

**Pipeline (L391–399):**

```
Import → Organize → Analyze → Plot → Customize → Validate → Export
```

**Hero note (L400):**
> **Core rule:** the researcher supplies the data and chooses the analysis. SCIX never invents
> experimental data, statistical results, or scientific conclusions.

## TOC index (L359–376)

`01` Main interface · `02` Navigation map · `03` Data workspace · `04` Graph creation wizard ·
`05` Graph editor · `06` Advanced plotting · `07` Statistics wizard · `08` Significance
annotation · `09` Publication figure designer · `10` Journal figure presets · `11` Graph
templates · `12` Research figure audit · `13` Reproducibility panel · `14` Universal discipline
engine · `15` Technical architecture · `16` Database structure · `17` Differentiators ·
`18` Product architecture & roadmap

---

## §01 Main interface (L404–428)

**Sub:** A three-pane layout familiar to researchers already using scientific plotting software,
with a modern shell around it.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SCIX   | Research Project: Nanomaterial Study              Save   Export     │
├──────────────────────────────────────────────────────────────────────────────┤
│ File  Data  Analysis  Plot  Statistics  Format  Journal  Validate  Help      │
├──────────────┬───────────────────────────────────────────────┬───────────────┤
│  PROJECT     │                GRAPH CANVAS                   │   PROPERTIES  │
│  Data        │        ┌─────────────────────────────┐        │ Chart Type    │
│  Worksheets  │        │        Publication          │        │ X Axis        │
│  Analyses    │        │          Figure             │        │ Y Axis        │
│  Graphs      │        │      ● ● ● ● ●              │        │ Error Bars    │
│  Tables      │        │    ● ● ● ● ●                │        │ Regression    │
│  Templates   │        └─────────────────────────────┘        │ Legend        │
│              │                                               │ Fonts         │
│              │                                               │ Symbols       │
│              │                                               │ Dimensions    │
├──────────────┴───────────────────────────────────────────────┴───────────────┤
│ Dataset: Experiment_01.xlsx | Rows: 120 | Columns: 8 | Analysis: ANOVA       │
└──────────────────────────────────────────────────────────────────────────────┘
```

## §02 Navigation map (L431–473)

**Sub:** Five top-level menus carry the whole workflow, from raw data to a submission-ready figure.

Note: the prose says "Five top-level menus"; the card grid renders **five** cards (DATA, ANALYSIS,
PLOT, FORMAT, EXPORT) while the §01 wireframe menu bar shows nine items (File, Data, Analysis,
Plot, Statistics, Format, Journal, Validate, Help). See [10-open-questions.md](./10-open-questions.md) Q1.

### DATA (L436–441)
Import Data · Data Table · Worksheet · Data Cleaning · Transformations · Filter · Sort · Group ·
Merge · Normalize · Calculate Column · Missing Values

### ANALYSIS (L443–449)
Descriptive Statistics · t-test · ANOVA · Multiple Comparison · Correlation · Regression ·
Nonlinear Regression · Dose-Response · Survival Analysis · ROC Analysis · Time-Series ·
Multivariate · Custom Analysis

### PLOT (L451–457)
New Graph · Gallery · XY · Line · Scatter · Column · Bar · Grouped · Stacked · Box · Violin ·
Histogram · Area · Heatmap · Contour · Survival · ROC · Calibration · Spectra · Kinetic Plot

### FORMAT (L459–465)
Axes · Labels · Fonts · Symbols · Lines · Error Bars · Legends · Grid · Colors · Panel Layout ·
Annotations · Equations · Significance · Figure Size

### EXPORT (L467–471)
PNG · TIFF · JPEG · SVG · PDF · EPS · DOCX · PPTX · LaTeX

## §03 Origin-style data workspace (L476–496)

**Sub:** A spreadsheet environment in the spirit of established scientific worksheet software.

```
┌───────────────────────────────────────────────────────────────┐
│ Worksheet 1                                                   │
├────┬──────────┬──────────┬──────────┬──────────┬─────────────┤
│ #  │ Time     │ Control  │ Sample A │ Sample B │ Sample C    │
├────┼──────────┼──────────┼──────────┼──────────┼─────────────┤
│ 1  │ 0        │ 0.00     │ 0.00     │ 0.00     │ 0.00        │
│ 2  │ 10       │ 0.12     │ 0.25     │ 0.31     │ 0.28        │
│ 3  │ 20       │ 0.21     │ 0.44     │ 0.51     │ 0.47        │
│ 4  │ 30       │ 0.33     │ 0.62     │ 0.69     │ 0.64        │
│ 5  │ 40       │ 0.42     │ 0.77     │ 0.82     │ 0.79        │
└────┴──────────┴──────────┴──────────┴──────────┴─────────────┘
```

### Every column supports (L490–495)
- Column name · Unit · Data type
- X/Y designation · Replicate designation · Group designation
- Error column · Formula · Metadata

## §04 Graph creation wizard (L499–541)

**Sub:** Clicking "New Graph" walks the researcher through four steps.

### STEP 1 — SELECT DATA
```
Dataset:  Experiment_01.xlsx / Worksheet 1

X Variable   [ Time ▼ ]
Y Variable   [ Sample A ▼ ]
Error        [ SD ▼ ]

☐ Include replicates
☐ Normalize data
☐ Include missing values
```

### STEP 2 — SELECT GRAPH
```
[ XY ]        [ Line ]        [ Scatter ]
[ Column ]    [ Grouped ]     [ Box Plot ]
[ Violin ]    [ Histogram ]   [ Heatmap ]
[ Survival ]  [ ROC ]         [ Dose Response ]
[ Spectrum ]  [ Kinetics ]    [ Calibration ]
```

### STEP 3 — STATISTICAL ANALYSIS
```
○ None
○ Descriptive statistics
○ t-test
○ One-way / Two-way ANOVA
○ Tukey
○ Correlation
○ Linear / Nonlinear regression
○ Custom
```

### STEP 4 — FORMATTING
> Opens the full Graph Editor with the chosen data, graph type and analysis already attached to
> the figure.

## §05 Graph editor (L545–588)

**Sub:** The strongest surface in the product — a left toolbar for drawing, a top toolbar for the
file lifecycle, and a right panel for every graph property.

### LEFT TOOLBAR
```
Select · Move
Zoom · Pan · Crosshair
Text · Arrow · Line
Shape
Significance
Annotation
```

### TOP TOOLBAR
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

### RIGHT PANEL
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

## §06 Origin-style advanced plotting (L592–621)

**Sub:** Curve fitting and peak analysis for spectroscopy, chromatography, and materials work.

### CURVE FITTING
- Linear · Polynomial
- Exponential · Logarithmic · Power
- Gaussian · Lorentzian · Sigmoidal
- Custom equation

### DISPLAYED WITH EVERY FIT
- Equation · R² · Adjusted R²
- Residuals · Confidence interval
- Parameter estimates · Standard error · p-value

### PEAK ANALYSIS
- Peak detection · Peak position
- Peak height · Peak area
- FWHM · Baseline
- Peak fitting

Accompanying note: Particularly relevant for spectroscopy, chromatography, and materials-science
datasets.

## §07 Prism-style statistics wizard (L625–656)

**Sub:** SCIX explains what a test does; the researcher decides whether it's the right one.

### WHAT TYPE OF DATA DO YOU HAVE?
```
[ Column ]  [ Grouped ]  [ XY ]  [ Survival ]  [ Contingency ]
```

### SELECT ANALYSIS
```
Descriptive
  Mean · Median · SD · SEM · CV · CI

Comparison
  t-test · Paired t-test
  ANOVA · Two-way ANOVA
  Multiple comparisons

Correlation
  Pearson · Spearman

Regression
  Linear · Polynomial · Nonlinear

Clinical
  ROC · Survival · Kaplan-Meier
```

## §08 Significance annotation (L660–670)

**Sub:** Automatic placement of significance markers — derived only from the analysis actually run.

```
          ***
       ─────────
   ●       ●

  Control   Treatment

markers:  *   **   ***   ****   ns   p = 0.032   p < 0.001
```

## §09 Publication figure designer (L673–704)

**Sub:** A dedicated mode for assembling submission-ready, multi-panel figures.

### FIGURE SIZE
```
☐ Single column
☐ 1.5 column
☐ Double column
☐ Custom

Width:  85 mm
Height: 65 mm
DPI:    600
```

### TYPOGRAPHY
```
Font · Size
Bold · Italic
Superscript · Subscript
Scientific notation
```

### MULTI-PANEL LAYOUT
```
┌──────────────┬──────────────┐
│     (a)      │      (b)     │
│              │              │
├──────────────┼──────────────┤
│     (c)      │      (d)     │
│              │              │
└──────────────┴──────────────┘
```

Accompanying note: Graphs are dragged into panels and aligned automatically.

## §10 Journal figure presets (L708–720)

**Sub:** Verified formatting profiles per target journal, with the source of each rule always visible.

```
TARGET JOURNAL
[ Select Journal ]

Figure requirements
────────────────────
Width · Height · Resolution
File format · Font
Maximum panels · Color requirements
```

Accompanying note: The system shows the source and date of each journal requirement rather than
silently assuming outdated rules.

## §11 Graph templates (L724–738)

**Sub:** Reusable, discipline-independent starting points that researchers can customize and save.

Ten templates, each marked with a ★:

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

## §12 Research figure audit (L741–759)

**Sub:** A pre-export checklist unique to SCIX — the first layer of the Research Integrity system.

All items ✓ except the last, which is ⚠:

```
✓  Dataset connected
✓  X-axis assigned
✓  Y-axis assigned
✓  Units specified
✓  Error bars identified
✓  Statistical method recorded
✓  Statistical values calculated
✓  Figure resolution acceptable
✓  Axis labels present
✓  Legend present
✓  Figure number assigned
⚠  Y-axis unit has not been specified
```

## §13 Reproducibility panel (L763–779)

**Sub:** Every figure carries its own provenance record, traceable back to the source dataset.

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

## §14 Universal discipline engine (L782–815)

**Sub:** Plot Studio is not restricted to any one field.

| Discipline | Capabilities |
|-----------|--------------|
| **Chemistry** | UV-Vis · FTIR · XRD · Chromatography · Calibration curves · Kinetics |
| **Biology / Medicine** | Dose-response · Cell viability · Survival curves · ROC · Box & violin plots |
| **Materials Science** | XRD · SEM/EDS data · Stress-strain · TGA/DSC · Photocatalytic kinetics |
| **Engineering** | Stress-strain · Load-displacement · Frequency response · Control-system plots · Performance curves |
| **Computer Science** | Accuracy · Precision / recall · ROC · Confusion matrix · Training curves · Benchmarks |
| **Agriculture** | Growth curves · Yield comparison · Treatment experiments · Environmental measurements |
| **Social Sciences** | Survey distributions · Likert-scale analysis · Correlation · Regression · Group comparison |

## §15 Technical architecture (L818–843)

**Sub:** A layered stack from interface down to export.

```
SCIX PLOT STUDIO
↓
FRONTEND LAYER — Next.js / React
   Data · Graph · UI
↕
BACKEND LAYER — FastAPI / Python
   Analysis · Export · Validation
↓
SCIENTIFIC ENGINE
   NumPy · Pandas · SciPy · Statsmodels · SymPy
↓
VISUALIZATION
   Matplotlib · Plotly
↓
EXPORT ENGINE
   TIFF · PNG · SVG · PDF · EPS · DOCX · PPTX · LaTeX
```

## §16 Database structure (L846–886)

**Sub:** A PostgreSQL entity set, with a project as the root of every record.

### CORE ENTITIES (19, listed in source order)
```
users                  projects
datasets               worksheets
columns                data_transformations
statistical_analyses    analysis_parameters
graphs                 graph_series
graph_axes             graph_annotations
graph_templates        figures
figure_panels          journal_presets
exports                audit_logs
versions
```

### RELATIONSHIP
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

## §17 What differentiates SCIX (L890–909)

**Sub:** Three pillars, the third of which moves SCIX beyond a graphing tool.

| | Pillar | Body |
|---|--------|------|
| ① | Origin-style plotting | A powerful data → analysis → graph workflow for demanding scientific plots. |
| ② | Prism-style statistics | Statistics → visualization → significance → publication, in one continuous path. |
| ③ | Research integrity | Data → analysis → figure → manuscript, as a reproducible research record. |

## §18 Final product architecture & roadmap (L913–970)

**Sub:** Plot Studio sits between the Writing and Literature modules, feeding a shared Research
Integrity layer and Export Center.

### Product architecture diagram (L917–939)
```
                          SCIX
              SCIENTIFIC RESEARCH PLATFORM
                              │
 ┌────────────────────────────┼────────────────────────────┐
 │                            │                            │
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

### Recommended development priority (L942–968)

| Release | Title | Body |
|---------|-------|------|
| `RELEASE 1 — CORE` | Foundation | Data table, import, basic graphs, formatting, PNG/PDF export. |
| `RELEASE 2 — SCIENTIFIC` | Analytical depth | Regression, error bars, curve fitting, statistics, publication-quality export. |
| `RELEASE 3 — PRISM-STYLE` | Statistical workflow | ANOVA, t-tests, multiple comparisons, dose-response, survival, ROC. |
| `RELEASE 4 — ORIGIN-STYLE` | Advanced plotting | Advanced fitting, peak analysis, layered graphs, batch plotting, templates. |
| `RELEASE 5 — RESEARCH INTELLIGENCE` | Integrity layer | Figure audit, reproducibility, journal presets, manuscript integration, full audit trail. |

### Closing statement (L970)
> This sequence is meant to make SCIX Plot Studio a serious scientific visualization component
> rather than a charting feature, while holding to the central principle: the researcher owns the
> science; SCIX provides the professional tools to analyze, visualize, organize, and publish it.

## S2 client-side behaviour (L978–990)

A ~12-line vanilla-JS scroll-spy: collects all `.toc-list a` anchors, maps them to their target
sections, and on `scroll` (passive listener) computes `window.scrollY + 120` to set the last
section whose `offsetTop` is above that position as `.active`. Runs once on load.
No framework, no dependencies.
