# SCIX / NM Scientific Research Studio — Extracted Specification

Complete, loss-free extraction of the product information contained in the two source HTML
documents in the repository root. This folder is the single source of truth for building the
software.

## Source documents

| # | File | Type | Size | Version |
|---|------|------|------|---------|
| S1 | `../nm-scientific-research-studio.html` | Product concept / landing page | 24 KB | — (no version stated) |
| S2 | `../scix-plot-studio.html` | Internal product specification | 38 KB | **v0.1** (internal draft) |

Both carry the footer attribution **NM GROUP OF INDUSTRIES & RESEARCH FOUNDATION**.

---

## Document index

| Doc | File | Contents |
|-----|------|----------|
| 00 | [00-source-extract.md](./00-source-extract.md) | Verbatim text of both HTML files, section by section. Nothing paraphrased. Use for traceability. |
| 01 | [01-product-vision.md](./01-product-vision.md) | Product identity, core principles, allowed/forbidden capability lists, target disciplines. |
| 02 | [02-writing-module.md](./02-writing-module.md) | The 6 language tools, the consistency checker, the 5-dimension pre-submission checker. |
| 03 | [03-plot-studio.md](./03-plot-studio.md) | All 18 sections of the SCIX Plot Studio specification. |
| 04 | [04-architecture.md](./04-architecture.md) | Technology stack, layer model, core API surface, product architecture diagram. |
| 05 | [05-data-model.md](./05-data-model.md) | PostgreSQL entity set, relationship tree, field-level design notes. |
| 06 | [06-integrity-authorship.md](./06-integrity-authorship.md) | Authorship policy matrix, research-integrity layer, figure audit, reproducibility panel. |
| 07 | [07-disciplines-terminology.md](./07-disciplines-terminology.md) | Discipline matrix, per-discipline plotting capabilities, terminology rules. |
| 08 | [08-roadmap.md](./08-roadmap.md) | 4 platform stages + 5 Plot Studio releases, merged into a sequenced build plan. |
| 09 | [09-design-tokens.md](./09-design-tokens.md) | Both design systems extracted from CSS: colors, type, spacing, components. |
| 10 | [10-open-questions.md](./10-open-questions.md) | Every gap, ambiguity and undecided decision found in the sources. |

---

## The one-paragraph summary

SCIX (also branded **NM Scientific Research Studio**) is a scientific writing, data analysis and
publication platform for researchers. Its defining constraint is that **the researcher owns all
science** — ideas, data, interpretation, results and citations are human-only. The software is
permitted to correct language, structure, terminology, formatting, statistics, figures and
formatting, and is forbidden from generating research claims, experimental results, references or
any scientific content. Every automated edit is labelled with its author (HUMAN / SOFTWARE) at the
moment it is made. The product has three top-level modules — **Writing**, **Plot Studio** and
**Literature** — which feed a shared **Research Integrity** layer and a **Journal Preparation**
layer, terminating in an **Export Center** (DOCX · PDF · LaTeX · PPTX).

## Non-negotiable rule (appears in both sources)

> "the researcher supplies the data and chooses the analysis. SCIX never invents experimental
> data, statistical results, or scientific conclusions." — S2, hero note
>
> "the researcher provides the ideas, data, interpretation and scientific content. The software
> corrects language, structure, formatting and presentation without inventing scientific
> information." — S1, hero note

This rule is a **product invariant**. Every module, feature and data model in these documents must
be traceable to it. See [06-integrity-authorship.md](./06-integrity-authorship.md).

## Reading order for development

1. [01-product-vision.md](./01-product-vision.md) — what the product is and is not
2. [04-architecture.md](./04-architecture.md) — how it is built
3. [05-data-model.md](./05-data-model.md) — how data is stored
4. [08-roadmap.md](./08-roadmap.md) — what is built first
5. [02](./02-writing-module.md) / [03](./03-plot-studio.md) / [06](./06-integrity-authorship.md) / [07](./07-disciplines-terminology.md) — feature detail
6. [10-open-questions.md](./10-open-questions.md) — resolve before committing to a schema
