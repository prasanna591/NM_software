# 07 — Disciplines & Terminology

Consolidated from S1 §One Core, Every Field (L417–431), S1 §terminology tools (L301, L306),
S2 §14 (L782–815), S2 §11 templates (L724–738).

---

## 7.1 The discipline model

**Stated model (S1 L421):**
> Each discipline carries its own terminology, manuscript templates, statistical methods, and
> journal formats — on the same shared SCIX core.

### Four things vary per discipline

| Dimension | Example from source | Consumer |
|-----------|--------------------|----------|
| **Terminology** | `nano particle` → `nanoparticle`; `bio sensor` → `biosensor` | Terminology checker, consistency checker |
| **Manuscript templates** | Not enumerated | Writing module |
| **Statistical methods** | Not enumerated, but implied — survival/ROC for medicine, calibration for chemistry | Statistics wizard defaults |
| **Journal formats** | Not enumerated | Journal presets, export |

### Critical architectural implication

The *core* is shared and the *profiles* are data. Therefore a discipline profile is a first-class
configurable record — **not** a hardcoded switch in the codebase. Neither source names a
`disciplines` or `discipline_profiles` entity; it must be added (see
[05-data-model.md](./05-data-model.md) §5.3).

### Proposed discipline profile structure

Derived from the four stated dimensions. Not in the source — engineering proposal.

| Field | Type | Purpose |
|-------|------|---------|
| key | slug | `chemistry`, `biology`, … |
| display_name | text | |
| terminology_rules | jsonb / FK rows | Compound-word, notation, unit rules |
| manuscript_template_id | FK | Section skeleton, headings |
| preferred_tests | enum[] | Defaults in the statistics wizard |
| default_graph_types | enum[] | Defaults in the plot gallery |
| default_templates | FK → graph_templates | §11 starters |
| journal_preset_ids | FK[] | Candidate target journals |
| notation_rules | jsonb | Gene/protein, math, formula conventions |

## 7.2 Discipline roster — platform level (17)

S1 L422–429. This is the platform's stated coverage.

| # | Discipline | # | Discipline |
|---|-----------|---|-----------|
| 1 | Chemistry | 10 | Computer Science |
| 2 | Physics | 11 | AI / Data Science |
| 3 | Biology | 12 | Mathematics |
| 4 | Biotechnology | 13 | Environmental Science |
| 5 | Medicine | 14 | Psychology |
| 6 | Pharmacy | 15 | Economics |
| 7 | Agriculture | 16 | Management |
| 8 | Engineering | 17 | Education |
| 9 | — | 18 | Social Sciences |
| | | 19 | Humanities |

*(19 listed in the source chip list; the source text says "Every field" without a count. Counted
from L422–429: Chemistry, Physics, Biology, Biotechnology, Medicine, Pharmacy, Agriculture,
Engineering, Computer Science, AI/Data Science, Mathematics, Environmental Science, Psychology,
Economics, Management, Education, Social Sciences, Humanities = **19**.)*

## 7.3 Discipline coverage — Plot Studio level (7)

S2 §14 names a different, smaller set with per-discipline plotting capabilities:

| Discipline | Named capabilities |
|-----------|-------------------|
| **Chemistry** | UV-Vis · FTIR · XRD · Chromatography · Calibration curves · Kinetics |
| **Biology / Medicine** | Dose-response · Cell viability · Survival curves · ROC · Box & violin plots |
| **Materials Science** | XRD · SEM/EDS data · Stress-strain · TGA/DSC · Photocatalytic kinetics |
| **Engineering** | Stress-strain · Load-displacement · Frequency response · Control-system plots · Performance curves |
| **Computer Science** | Accuracy · Precision / recall · ROC · Confusion matrix · Training curves · Benchmarks |
| **Agriculture** | Growth curves · Yield comparison · Treatment experiments · Environmental measurements |
| **Social Sciences** | Survey distributions · Likert-scale analysis · Correlation · Regression · Group comparison |

**Discrepancy (Q3):** the two lists do not match.
- S2 names **Materials Science**, which is absent from S1's 19.
- S1 names 12 disciplines S2 never mentions: Physics, Biotechnology, Pharmacy, AI/Data Science,
  Mathematics, Environmental Science, Psychology, Economics, Management, Education, Humanities,
  Computer Science appears in both but with different framing.
- S2 groups "Biology / Medicine" into one card; S1 lists them separately.

Materials Science is almost certainly intended to sit under Chemistry or Engineering in S1's list.
The two lists must be reconciled into one canonical roster.

## 7.4 Capability-to-discipline mapping

Cross-referencing the plot gallery (§02 PLOT), statistics wizard (§07), advanced plotting (§06)
and §14:

| Capability | Named for |
|-----------|-----------|
| XY, Line, Scatter | Universal |
| Column, Bar, Grouped, Stacked | Universal |
| Box, Violin, Histogram, Area | Universal; explicitly Biology/Medicine, Social Sciences |
| Heatmap, Contour | Materials, Engineering |
| Survival, Kaplan-Meier | Biology/Medicine |
| ROC | Biology/Medicine, Computer Science |
| Calibration | Chemistry |
| Spectrum / Spectra | Chemistry, Materials |
| Kinetic | Chemistry, Biology, Materials |
| Dose Response | Biology/Medicine, Biology |
| Curve fitting (9 models) | Universal |
| Peak analysis | Chemistry (spectroscopy, chromatography), Materials |
| Time-series | Universal |
| Multivariate | Universal |
| Confusion matrix | Computer Science |
| Training curves, Benchmarks | Computer Science |
| Stress-strain | Materials, Engineering |
| Load-displacement, Frequency response, Control-system plots | Engineering |
| TGA/DSC, SEM/EDS | Materials |
| Photocatalytic kinetics | Materials, Chemistry |
| Growth curves, Yield comparison | Agriculture |
| Likert-scale analysis | Social Sciences |

Note **Likert-scale analysis** (S2 L812) is not covered by any named graph type or test in the
spec — it needs a treatment (ordinal data handling, median/IQR reporting, appropriate correlation
such as Spearman). Gap — Q13.

## 7.5 Graph templates

Ten starters (S2 L727–737), each ★-marked, all discipline-independent and user-customisable:

| # | Template | Likely home discipline |
|---|----------|----------------------|
| 1 | Materials Characterization | Materials Science |
| 2 | Photocatalytic Study | Materials Science / Chemistry |
| 3 | Biological Assay | Biology |
| 4 | Cell Viability | Biology / Medicine |
| 5 | Dose Response | Biology / Medicine |
| 6 | Kinetic Study | Chemistry |
| 7 | Survey Analysis | Social Sciences |
| 8 | Engineering Experiment | Engineering |
| 9 | Regression | Universal |
| 10 | Spectroscopy | Chemistry / Materials |

Templates are stored in `graph_templates` with `is_system = true`; users clone and customise.

## 7.6 Terminology rules

### Rule families

Derived from S1 L301 (terminology tool) and L306 + L310–316 (consistency tool):

| Family | Detection | Canonical form | Example |
|--------|-----------|----------------|---------|
| **Closed compounds** | Known multi-word technical terms written separately | Join | `nano particle` → `nanoparticle`, `bio sensor` → `biosensor` |
| **Chemical formula subscripting** | Element-symbol + digit adjacency | Unicode subscripts | `CeNiO3` → `CeNiO₃` |
| **Chemical formula superscripting** | Charge/oxidation-state notation | Unicode superscripts | not shown; implied by §09 typography controls |
| **Dash style** | `-` between compound terms | en-dash `–` | `UV-Vis` → `UV–Vis` |
| **Number–unit spacing** | Digit immediately followed by a unit token | Insert space | `10mg` → `10 mg` |
| **Figure reference form** | `Fig.` / `Fig` / `Figure` / `FIG.` | One chosen form | `Fig. 1` → `Figure 1` |
| **Table reference form** | `Tab.` / `Table` | One chosen form | implied by §TABLES checks |
| **Spelling locale** | US vs UK variants | One chosen locale | `color` / `colour` |
| **Gene notation** | Species conventions (italic, case) | Per discipline | §09 offers italic/superscript/subscript controls |
| **Protein notation** | Case conventions | Per discipline | |
| **Math notation** | Variable/variable formatting | Per discipline | |
| **Defined-term capitalisation** | First use vs subsequent | One chosen form | |

### Two-phase consistency algorithm

Stated in S1 L306: "Catches … **then applies one chosen style throughout**."

```
1. SCAN     Walk the document, match every rule family, collect all occurrences
2. GROUP    Cluster matches by (rule_family, canonical_concept) → variant set
            e.g. { "CeNiO3": 4 occurrences, "CeNiO₃": 1 occurrence }
3. RANK     Order variants by frequency; offer the most frequent as the suggested default
4. CHOOSE   The researcher picks the canonical variant (or types a new one)
5. APPLY    Replace every occurrence doc-wide
6. RECORD   Write one audit_log entry per change, attribution = SOFTWARE,
            actor_component = "consistency"
```

**Step 3 matters.** Frequency-ranking the default makes the common case one click. **Step 6 is
mandatory** — this is a document-wide automated rewrite and rule R5 requires attribution on every
single replacement, not one summary entry. Practically: one `audit_logs` row per replacement, all
sharing a `batch_id`.

### Discipline-sensitivity

"**per discipline**" (S1 L301) means the same string can be correct in one field and wrong in
another. Examples:

| String | Chemistry | Biology |
|--------|-----------|---------|
| `E. coli` | Wrong — italic *E. coli*, species binomial | Correct |
| `pH` | Correct | Correct (no space) |
| `p K` | Wrong — `pK` no space | Wrong |
| `min` | Ambiguous — time unit vs. minimum | Ambiguous |

So terminology rules are scoped `rule → discipline[]`, and only rules whose discipline scope
includes the project's discipline are evaluated. This makes the discipline profile a functional
dependency of the writing engine, not documentation.

## 7.7 Style choices the user must configure

The source implies these are user- or project-level settings, since the checker must apply "one
chosen style":

| Setting | Example value | Default |
|---------|--------------|---------|
| Figure reference form | `Figure 1` / `Fig. 1` | `Figure 1` |
| Table reference form | `Table 1` / `Tab. 1` | `Table 1` |
| Dash style | en-dash / hyphen | en-dash |
| Spelling locale | US / UK | US |
| Formula notation | Unicode subscripts / LaTeX / plain | Unicode |
| Citation style | APA / MLA / Vancouver / IEEE / Chicago | per journal preset |
| Active or passive voice | prefer active / prefer passive | prefer active |
| Register | academic / concise / formal | academic |

Citation style is notable: it is set by the target journal preset, so journal selection and
consistency resolution are coupled.
