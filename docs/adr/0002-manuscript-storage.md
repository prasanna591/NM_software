# ADR 0002 — Manuscript storage model

**Status:** Accepted
**Date:** 2026-10-03
**Closes:** Q10 (docs/10-open-questions.md)
**Impact:** The entire Writing module, which had no data model in the source spec

---

## Context

`docs/10-open-questions.md` Q10, blocking:

S1 names `manuscripts → sections, revisions` and defines `POST /api/manuscripts`. S1's five
pre-submission STRUCTURE checks require heading hierarchy and section detection. The §REFERENCES
dimension requires a bibliography. `tables` is named in S1 and has four dedicated checks.

**S2's 19-entity schema contains none of these** — no manuscript, section, revision, table or
reference entity. Half the specified product has no storage model.

The Writing module also needs to store *machine-generated suggestions and their human decisions*,
which neither source names but which rule R6 (accept/edit/reject) makes mandatory.

## Decision

Six new entities, plus two tables for the suggestion workflow.

### Document model

```
manuscripts          1 ── N  sections
sections                 ── N  manuscript_tables
manuscript_revisions  1 ── N  sections        (version history)
references             1 ── N  citation_links
citation_links            ──   section ↔ reference (position, intent)
```

### Key choices

**`sections` are flat with `ordinal` + `heading_level`, not nested.** A tree would model heading
hierarchy more directly, but every real manuscript editor (and DOCX itself) needs linear document
order for export, and heading hierarchy is recoverable from `heading_level`. Flat is simpler,
exports correctly, and the §STRUCTURE "heading hierarchy" check becomes a scan for skipped levels.

**`manuscript_revisions` snapshots the whole manuscript as JSONB**, with `section_id` nullable —
null means a full-manuscript revision. Whole-document snapshots at manuscript scale (a journal
article is ~10⁵ characters) are cheap and make diffs trivial. Per-section snapshots would need a
reassembly algorithm for no benefit.

**`references` store only user-supplied or registry-verified metadata.** `verification_status` is
one of `unverified` / `doi_verified` / `registry_verified`. Rule R4 forbids generated references;
there is no code path that creates a `references` row without either user input or a registry
response. `registry_verified` requires a `registry` + `registry_fetched_at` — see §11.7 of the
build strategy.

**`citation_links` is a join table**, not a column on `sections`. The §REFERENCES dimension requires
three reconciliations — missing, duplicate, unused — and all three are set operations over citation
links. Without an explicit link table, "unused references" is undetectable.

**Suggestions are first-class and separate from `sections`.** `writing_suggestions` holds the
machine output, `suggestion_decisions` holds the human response. A suggestion outlives its section
version; the decision references the revision it was applied against, so a version diff can
reconstruct exactly what changed.

### `writing_suggestions`

| Field | Notes |
|-------|-------|
| `id` | PK |
| `section_id` | FK |
| `revision_id` | the text version it was computed against |
| `tool` | `grammar` \| `sentence` \| `register` \| `paragraph` \| `terminology` \| `consistency` |
| `rule_id` | e.g. `number_unit_spacing` |
| `severity` | `info` \| `warn` \| `error` |
| `offset_start` / `offset_end` | character range in the source text |
| `original_text` / `suggested_text` | verbatim — the diff component renders these |
| `deletions` / `insertions` | jsonb token lists |
| `batch_id` | groups a document-wide consistency run |
| `status` | `pending` \| `accepted` \| `edited` \| `rejected` \| `superseded` |

**`superseded` matters.** A consistency run rewrites the whole document; earlier pending suggestions
whose ranges no longer match are superseded, not silently left to fail on apply.

### `suggestion_decisions`

| Field | Notes |
|-------|-------|
| `id` | PK |
| `suggestion_id` | FK |
| `decision` | `accept` \| `edit` \| `reject` |
| `final_text` | set when `decision = 'edit'` — the researcher's version |
| `decided_by` | FK → users. NOT NULL. Rule R6: no suggestion may be applied without a human decision. |
| `decided_at` | |
| `applied_result` | the actual before/after written to the section |

### `manuscript_tables`

Separate from `figures`/`tables` in the data layer because their checks differ:

| Field | Notes |
|-------|-------|
| `id`, `section_id`, `ordinal` | |
| `number` | "Table 1" |
| `caption` | §TABLES check: captions |
| `column_headers` | jsonb |
| `row_count` | |
| `units` | §TABLES check: units |
| `referenced_in_text` | §TABLES check: in-text references |

The in-text reference check reads `citation_links`-adjacent data — or, more simply, a text scan for
"Table N". A dedicated flag is stored for the check's result but derived from the scan at check time.

## Invariants

| Constraint | Reason |
|-----------|--------|
| `suggestion_decisions.decided_by` NOT NULL | R6 — no automated application path exists |
| `sections.ordinal` unique per manuscript | export order |
| `sections.heading_level` between 1 and 6 | §STRUCTURE heading hierarchy |
| `references.verification_status = 'registry_verified'` requires `registry` NOT NULL | R4 |
| No `references` row without user input or registry response | R4, enforced in the service layer |

## Consequences

The Writing module now has a storage model, which unblocks Phase 2 of the build strategy
(docs/11-build-strategy.md §11.8). The cost is 8 new tables in migration #1 — but these are
additive and low-risk, unlike the two *retrofitting* constraints (`audit_logs.attribution`,
ordered `data_transformations`) which are genuinely irreversible.
