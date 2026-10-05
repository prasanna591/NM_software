# 02 — Writing Module & Manuscript Checker

Derived from `nm-scientific-research-studio.html` §Language & Writing Module (L271–318) and
§Pre-submission (L320–348).

---

## 2.1 Module scope

**Heading (L274):** Every layer of language, checked — none of the science, touched

**Principle (L275):** From single-word grammar fixes to full-manuscript consistency, each tool
acts only on **how something is said**, never on **what it claims**.

The module operates on a granularity ladder. Each rung is a separate, individually selectable tool
— not one monolithic "improve my paper" button.

| Rung | Granularity | Tool |
|------|-------------|------|
| 1 | Word | Grammar correction, Terminology checker, Consistency checker |
| 2 | Sentence | Sentence formation |
| 3 | Paragraph | Paragraph-level checking |
| 4 | Register / style | Scientific language improvement |
| 5 | Document | Consistency checker, Pre-submission checker |

## 2.2 Tool 01 — Grammar correction

**Tag:** `01 · GRAMMAR`

Full check list from L281, 11 categories:

| Category | Notes |
|----------|-------|
| Tense | |
| Subject–verb agreement | |
| Articles | a / an / the — a known problem area for non-native writers |
| Prepositions | |
| Plurals | |
| Pronouns | |
| Punctuation | |
| Spelling | also a standalone capability in the YES list |
| Capitalization | |
| Fragments | |
| Run-ons | |

**Output type:** single-word / single-token replacement suggestions. No rewrites.

## 2.3 Tool 02 — Sentence formation

**Tag:** `02 · SENTENCES`

> Rough, non-native phrasing rebuilt into correct scientific English — the researcher approves
> every change. (L286)

This is the most aggressive tool in the module: it *rebuilds* a sentence rather than patching it.
The approval requirement in this sentence is explicit in the source and is a hard requirement (R6).

**Output type:** whole-sentence replacement, presented as a diff, requiring an explicit decision.

## 2.4 Tool 03 — Scientific language improvement (register)

**Tag:** `03 · REGISTER`

> Academic English, concise or formal phrasing, active/passive voice, readability, redundancy,
> flow — as selectable options. (L291)

"as selectable options" is a design instruction: these are **independent toggles**, not one
"improve style" action. Proposed control set:

| Option | Type | Values |
|--------|------|--------|
| Register | select | Academic English / Concise / Formal |
| Voice | select | Keep as-is / Prefer active / Prefer passive |
| Readability | toggle | — |
| Redundancy removal | toggle | — |
| Flow / transitions | toggle | — |

**Output type:** phrasing-level suggestions.

## 2.5 Tool 04 — Paragraph-level checking

**Tag:** `04 · PARAGRAPH`

> Topic sentences, sequencing, repetition, transitions, coherence, sentence length, terminology
> consistency within a paragraph. (L296)

Seven checks, all structural rather than lexical:

| Check | What it looks for |
|-------|-------------------|
| Topic sentences | Paragraph opens with a clear topic sentence |
| Sequencing | Logical order of sentences within the paragraph |
| Repetition | Same idea restated |
| Transitions | Connective tissue between sentences |
| Coherence | Do the sentences actually relate |
| Sentence length | Sentences outside a comfortable length band |
| Terminology consistency | A term used two ways *within* the paragraph |

## 2.6 Tool 05 — Scientific terminology checker

**Tag:** `05 · TERMINOLOGY`

> "nano particle" → nanoparticle, "bio sensor" → biosensor — plus units, formulas, gene/protein
> notation, math notation, per discipline. (L301)

Two distinct operations:

1. **Compound-word joining** — hyphenated forms of closed compounds are wrong:
   `nano particle` → `nanoparticle`, `bio sensor` → `biosensor`
2. **Notation normalisation** — units, formulas, gene/protein notation, math notation

Critically, "**per discipline**" — the checker is discipline-profile-driven. The same string is
correct in one field and wrong in another.

## 2.7 Tool 06 — Consistency checker

**Tag:** `06 · CONSISTENCY`

> Catches CeNiO₃ vs CeNiO3, UV-Vis vs UV–Vis, Fig. 1 vs Figure 1 — then applies one chosen style
> throughout. (L306)

**Two-phase behaviour:**

1. **Detect** — scan the whole manuscript for competing variants of the same concept
2. **Resolve** — the researcher picks one canonical variant; apply it document-wide

### Documented examples (L310–316)

| Wrong | Right | Category |
|-------|-------|----------|
| `CeNiO3` | `CeNiO₃` | Chemical formula → Unicode subscripts |
| `UV-Vis` | `UV–Vis` | Dash style: hyphen → en-dash |
| `10mg` | `10 mg` | Number–unit spacing |
| `Fig. 1` | `Figure 1` | Abbreviation vs spelled-out figure reference |

### Category taxonomy to implement

The four examples imply at least these rule families. A `ConsistencyRule` must be data-driven, not
hardcoded per case:

| Family | Detection | Canonical target |
|--------|-----------|------------------|
| Chemical formula subscripting | `([A-Z][a-z]?\d*)` letter+digit adjacency | Unicode subscripts |
| Dash style | `-` between compound terms | en-dash `–` |
| Number–unit spacing | `\d+(unit)` | insert thin/normal space |
| Figure/Table reference form | `Fig.` / `Fig` / `Figure` | one chosen form |
| Spelling variants (US/UK) | `colour`/`color` | one chosen locale |
| Capitalisation of defined terms | first-use vs subsequent | one chosen form |

The rule engine therefore needs: **detect → group into a variant set → let the user choose the
winner → apply everywhere**. Frequency-ranked, so the most-used variant is offered as the
suggested default.

## 2.8 Pre-submission checker — five dimensions

**Heading (L323):** One manuscript checker, five dimensions
**Dek (L324):** Run before submission — language, structure, references, figures and tables, all
checked in the same pass.

This is a *different* feature from the six writing tools: it is a whole-document compliance pass,
not a set of individual editing tools. 25 discrete checks across 5 dimensions:

### Dimension 1 — LANGUAGE (5)
- [ ] Grammar
- [ ] Spelling
- [ ] Sentence formation
- [ ] Academic style
- [ ] Terminology

### Dimension 2 — STRUCTURE (6)
- [ ] Heading hierarchy
- [ ] Abstract
- [ ] Keywords
- [ ] Intro / Methods
- [ ] Results / Discussion
- [ ] Conclusion

### Dimension 3 — REFERENCES (5)
- [ ] Missing citations — a claim needing a citation that has none
- [ ] Duplicate references — same work entered twice
- [ ] Unused references — in the bibliography but never cited
- [ ] Citation numbering — sequence/ordering correctness
- [ ] Reference style — matches target style

### Dimension 4 — FIGURES (5)
- [ ] Figure numbering
- [ ] Captions
- [ ] In-text references — every figure is cited in the text
- [ ] Resolution
- [ ] Axis labels & units

### Dimension 5 — TABLES (4)
- [ ] Table numbering
- [ ] Captions
- [ ] Units
- [ ] In-text references

**Total: 25 checks.**

Missing citations + unused references + duplicate references together form a citation-integrity
triangle: the set of in-text citations, the set of bibliography entries, and the set of "claims
that need support" must reconcile. This is directly implementable and is a strong integrity
feature.

Note that FIGURES checks here overlap with the Plot Studio §12 figure audit (12 checks). They are
different scopes: this is manuscript-level (is the figure numbered, captioned, cited?), Plot Studio
is figure-level (does the figure have units and a legend?). Both must exist; see Q7.

## 2.9 The change-acceptance workflow

From the hero card (L244–258) — the canonical interaction for every suggestion in this module:

```
1. Show original text with deletions struck through
2. Show suggested revision with insertions highlighted
3. Offer exactly three actions:  Accept  |  Edit  |  Reject
```

**Requirements derived:**

- **Accept** — apply the suggestion verbatim
- **Edit** — open an editable variant of the suggestion, apply the researcher's version
- **Reject** — dismiss, and remember the rejection (so the same suggestion does not reappear)

Each action writes an `edit` record carrying an `attribution` of `SOFTWARE` and the tool that
produced it. See [06-integrity-authorship.md](./06-integrity-authorship.md).

Rejected suggestions must be persisted per-user, otherwise the same false positive resurfaces on
every check — a real usability failure for a tool meant to be run repeatedly.
