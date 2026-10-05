# 06 — Authorship Policy & Research Integrity Layer

This is the product's claimed differentiator. S1 §The Differentiator (L350–373) and S2 §12, §13,
§17. Everything here traces to a product invariant stated in
[01-product-vision.md](./01-product-vision.md) §1.3.

---

## 6.1 The authorship policy matrix

S1 L356–371. Status indicator: **HUMAN AUTHORSHIP MODE — ENABLED**.

| Item | Attribution | Rationale |
|------|-------------|-----------|
| Research content | 🟢 **HUMAN** | The ideas themselves |
| Research interpretation | 🟢 **HUMAN** | What the results mean |
| Experimental results | 🟢 **HUMAN** | The measurements |
| Grammar correction | 🔵 **SOFTWARE** | Language only |
| Spelling correction | 🔵 **SOFTWARE** | Language only |
| Formatting | 🔵 **SOFTWARE** | Presentation only |
| Statistical calculation | 🔵 **SOFTWARE** | Arithmetic on user data |
| Figure generation from user data | 🔵 **SOFTWARE** | Rendering user data |

### The pattern

The dividing line is **content vs. presentation**:

- Anything that decides, interprets, measures or concludes → HUMAN
- Anything that fixes language, computes arithmetic on supplied numbers, or renders → SOFTWARE

Note "Statistical calculation" is SOFTWARE but "Experimental results" is HUMAN. The platform may
compute a p-value; it may not produce the data that p-value describes.

### Visual encoding (from S1 CSS)

| State | Badge bg | Badge text | Dot |
|-------|----------|-----------|-----|
| HUMAN | `rgba(79,216,138,0.16)` | `#8be5ac` | `#4fd88a`, 4px glow |
| SOFTWARE | `rgba(122,166,255,0.16)` | `#9db9ff` | — |

Panel background `#1c1c1a` (ink), text `#c9c6ba` / `#9fd8b4`. The dark panel is deliberate: the
authorship status is presented as a system state, not marketing copy. **The "HUMAN AUTHORSHIP MODE —
ENABLED" indicator should persist in the product chrome**, not just the landing page — it is the
product's trust signal.

## 6.2 The timing requirement

> "Every change is labeled **at the moment it happens** — not disclosed after the fact." (S1 L354)

This rules out a batch post-processing disclosure screen. Consequences:

1. Each edit writes its attribution record **synchronously with the edit**, in the same transaction
2. There is no "review all AI changes at the end" flow — attribution is not a report, it is part of
   the edit
3. Undo of an edit must not erase its audit record — the log is append-only; undo is a *new* event

## 6.3 The approval requirement

Three mechanisms in the sources enforce human approval:

| Mechanism | Source | Applies to |
|-----------|--------|-----------|
| Accept / Edit / Reject per suggestion | S1 L253–257 | Every writing suggestion |
| "the researcher approves every change" | S1 L286 | Sentence formation specifically |
| "the researcher decides whether it's the right one" | S2 L627 | Statistical test selection |
| "the researcher supplies the data and **chooses the analysis**" | S2 L400 | All analysis |
| `selected_by` on every analysis record | derived, [05](./05-data-model.md) | Enforced at DB level |

**No path may apply a change without a recorded human decision.** Not a bulk "accept all", not a
background normalisation pass, not an autofix on save.

## 6.4 Attribution model

Two values only — `human` and `software`. Every mutating event carries one.

```json
{
  "attribution": "software",
  "actor_component": "grammar",
  "tool_version": "1.4.0",
  "action": "edit_accepted",
  "target": { "type": "section", "id": "…" },
  "before": "The material is showing very high activity because it is having good surface area.",
  "after":  "The material exhibited high activity, which may be associated with its large surface area.",
  "deletions": ["showing", "having"],
  "insertions": ["exhibited", "which may be associated with its large surface area"],
  "decision": "accept",
  "decided_by": "user-id",
  "created_at": "…"
}
```

### Storage rules

| Rule | Reason |
|------|--------|
| `attribution` denormalised onto every row | Must not require a join to know who wrote something |
| `audit_logs` append-only — no UPDATE, no DELETE | A mutable audit trail is not an audit trail |
| `actor_user_id` NULL ⟺ `attribution = 'software'` | Prevents attributing a machine edit to a person |
| `actor_user_id` NOT NULL ⟹ `attribution = 'human'` | Prevents laundering a machine edit through a user |
| `tool_version` on every software row | Reproducibility |

## 6.5 Enforcement points

The invariant must be defended at every layer, not just in the UI.

| Layer | Enforcement |
|-------|-------------|
| **UI** | Every suggestion shows Accept/Edit/Reject; no "apply all" |
| **API** | No endpoint mutates manuscript text without a `decision` in the request body |
| **Service** | Writing engine functions return *suggestions*, never mutations |
| **Analysis** | `POST /api/statistics/analyze` requires an explicit `test_name`; there is no "suggest a test" endpoint |
| **Annotations** | `graph_annotations.source_analysis_id` NOT NULL when `kind='significance'`; marker must match that analysis's p-value |
| **References** | No endpoint generates citation metadata; only stores what the user supplies |
| **Data** | No synthetic-data or imputation path exists |
| **DB** | CHECK constraints per §6.4 |
| **Export** | Provenance block emitted into exported files |

## 6.6 Research Integrity layer

Named as a platform layer in S2 §18 (L930–934). Four responsibilities:

| Responsibility | Implementation evidence |
|----------------|------------------------|
| **Audit trail** | `audit_logs` entity; `versions` entity; `attribution` on every change |
| **Reproducibility** | §13 provenance panel; `Trace Figure` action; library version pinning |
| **Version control** | S1 `manuscripts → sections, revisions`; `versions` entity; Stage 2 "version control" |
| **Data traceability** | §13 record; `graph_annotations.source_analysis_id`; dataset→worksheet→column→graph→figure chain |

S2 §17 calls this pillar ③ and states it is "what moves SCIX beyond a graphing tool".

## 6.7 The figure audit (§12)

12 pre-export checks. Implemented in `POST /api/graphs/{id}/audit`.

| # | Check | Derived from | Blocking? |
|---|-------|--------------|-----------|
| 1 | Dataset connected | §12 | Warn |
| 2 | X-axis assigned | §12 | Warn |
| 3 | Y-axis assigned | §12 | Warn |
| 4 | Units specified | §12 | Warn |
| 5 | Error bars identified | §12 | Warn |
| 6 | Statistical method recorded | §12 | Warn |
| 7 | Statistical values calculated | §12 | Warn |
| 8 | Figure resolution acceptable | §12 (600 DPI default, §09) | Warn |
| 9 | Axis labels present | §12 | Warn |
| 10 | Legend present | §12 | Warn |
| 11 | Figure number assigned | §12 | Warn |
| 12 | *Y-axis unit has not been specified* | §12 demo failure | **Warn (shown failing)** |

The source does not specify whether failures block export or merely warn. Given the product's
integrity positioning, **warn + require explicit acknowledgement** is the safer choice than a hard
block — a hard block on "legend present" would be unusable for single-series figures. See Q12.

### Relationship to the manuscript checker

Two distinct audits at different scopes. Both are required.

| | Plot Studio §12 | Manuscript checker §FIGURES |
|---|-----------------|--------------------------|
| Subject | One figure object | The manuscript's figure references |
| Checks | 12 | 5 |
| Focus | Is this figure scientifically complete? | Is every figure numbered, captioned, cited, adequately resolved, labelled with units? |
| Runs | Pre-export | Pre-submission |

## 6.8 The reproducibility panel (§13)

### The provenance record

Nine fields, reproduced in the source as `FIGURE 03`:

| Field | Example | Source entity |
|-------|---------|---------------|
| Source | `Experiment_01.xlsx` | `datasets.source_filename` |
| Data | `Worksheet 2` | `worksheets.name` |
| Processing | `Normalization → Log transformation` | `data_transformations` (ordered) |
| Analysis | `One-way ANOVA` | `statistical_analyses.test_name` |
| Post-hoc | `Tukey` | `statistical_analyses.posthoc_test` |
| Plot | `Grouped column` | `graphs.graph_type` |
| Error | `SD` | `graph_series.error_basis` |
| Created | `SCIX Plot Studio` | `actor_component` |
| Version | `v1.4` | `tool_version` |

All nine are derived from stored entities — the panel is a **query, not a stored blob**. Storing it
as a JSON blob would let it drift out of sync with the entities it summarises.

### Trace Figure

> "returns to the underlying dataset and analysis"

Requires, in order:
1. `figure_panels` → `graph_id` → `graph_series` → `y_column_id` → `worksheet_id` → `dataset_id`
2. `graphs.source_analysis_id` → `statistical_analyses` → `inputs` → column refs
3. `data_transformations` ordered by `seq` → replayable to reproduce the plotted values

Requirement 3 is the hard one. `Normalization → Log transformation` must be stored as an ordered,
parameterised, replayable chain — a single `normalized: true` flag will not satisfy Trace.

## 6.9 Manuscript-level reference integrity

The §REFERENCES dimension contributes to research integrity at manuscript level. Three checks form
a reconciliation triangle:

| Check | Failure mode |
|-------|-------------|
| Missing citations | A claim needing support with no citation |
| Duplicate references | The same work in the bibliography twice |
| Unused references | A bibliography entry never cited in text |

Reconciliation requires comparing three sets:
- `B` = bibliography entries
- `C` = in-text citation keys
- `N` = claims flagged as needing support

Healthy state: `B == C` (no unused, no missing), `B` has no duplicates, and every element of `N`
is covered by a citation at an acceptable position. Plus `Citation numbering` must be sequential
and match first-appearance order.

Note the interaction with rule R4: SCIX may *detect* that a claim needs a citation, and may *format*
citations to a target style — it may never *supply* the citation. The literature module stores what
the researcher provides.

## 6.10 Version control

S1 names `manuscripts → sections, revisions` (L399). Stage 2 (L446) lists "version control" as a
Stage 2 deliverable. `versions` is a listed entity (S2 L862).

Scope: at minimum manuscript sections and figures. Each version records author type, so a version
history doubles as an authorship history.

Requirement not stated in the source but implied by §06 Stage 3 ("research-integrity checks"):
a **diff view** between versions, and attribution shown on the diff — the same red/green treatment
as the hero diff card.

## 6.11 Traceability chain summary

The complete path a claim in a published paper can be traced back:

```
Published claim in manuscript
  └─ manuscript_section
       └─ versions[]                      (who wrote this sentence, HUMAN or SOFTWARE)
       └─ references[]                     (user-supplied citation)
       └─ figure_reference → figures
            └─ figure_panels → graphs
                 └─ graph_series → columns
                      └─ columns → worksheets → datasets   (the raw uploaded file)
                 └─ data_transformations[] (ordered, replayable)
                 └─ source_analysis_id → statistical_analyses  (test, params, results, posthoc)
                      └─ graph_annotations (significance markers, backed by this analysis)
            └─ figure_audits[]             (12-point audit history)
            └─ exports[]                   (what was submitted, in what format)
       └─ audit_logs[]                     (every event, append-only)
```

If any link in this chain is broken, the integrity claim fails. This chain is the acceptance
criterion for the Research Integrity layer.
