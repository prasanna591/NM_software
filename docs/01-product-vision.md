# 01 — Product Vision & Identity

Derived from `nm-scientific-research-studio.html`. Line references point at that file.

---

## 1.1 Naming

The two sources use two names for what is presented as one platform:

| Name | Where it appears | Role |
|------|------------------|------|
| **NM Scientific Research Studio** | S1 title, brand, footer | Customer-facing / company brand |
| **SCIX** | S1 authorship panel ("SCIX AUTHORSHIP POLICY"), "shared SCIX core"; S2 throughout | Internal product / platform codename |
| **SCIX Plot Studio** | S2 title and footer | The plotting module of SCIX |

**Implication for the software:** the repo/module namespace should be `scix`; the display brand is
`NM Scientific Research Studio`. Both must be selectable per deployment (white-label). Not stated
in the source — flagged as Q2 in [10-open-questions.md](./10-open-questions.md).

## 1.2 Tagline and positioning

**Eyebrow / tagline:**
> HUMAN-WRITTEN · SCIENTIFICALLY ORGANIZED · PUBLICATION READY

**Headline:**
> Your research, *written correctly* — never rewritten for you

**Positioning statement (L242):**
> A scientific writing and research platform that improves grammar, structure, terminology and
> formatting — without inventing a single scientific claim.

**Identity contrast (L266):**
> Not an **AI paper-writing service**. A **scientific writing and publication** platform.

**Explicit competitive framing (L354):**
> This is what separates a writing assistant from an **AI humanizer**.

The product's marketing angle is therefore *anti-AI-authorship*: it is positioned as the opposite
of tools that conceal machine authorship. Authorship transparency is the differentiator, not a
compliance afterthought.

## 1.3 The core principle (product invariant)

Stated twice, in both sources, in near-identical terms. This is the constraint the entire product
is built around.

> **S1 (L260):** "the researcher provides the ideas, data, interpretation and scientific content.
> The software corrects language, structure, formatting and presentation without inventing
> scientific information."

> **S2 (L400):** "the researcher supplies the data and chooses the analysis. SCIX never invents
> experimental data, statistical results, or scientific conclusions."

> **S2 (L970):** "the researcher owns the science; SCIX provides the professional tools to analyze,
> visualize, organize, and publish it."

Decomposed into testable rules:

| # | Rule | Enforceable as |
|---|------|----------------|
| R1 | The system never produces a scientific claim | No endpoint returns generated prose about findings; writing engine operates on the user's text only |
| R2 | The system never produces experimental data | No synthetic/imputed data path in the data engine |
| R3 | The system never produces statistical results on its own initiative | `POST /api/statistics/analyze` requires an explicit named test in the request body |
| R4 | The system never generates references | Literature module stores user-supplied citations only; no DOI autocompletion that fabricates metadata |
| R5 | Every automated change is attributed at the moment it occurs | Mandatory `attribution` field on every edit record; no post-hoc-only disclosure |
| R6 | The researcher approves every language change | No write path that mutates manuscript text without an explicit accept/edit/reject decision |

R5 and R6 are the two that the source treats as the product's moat. They are specified in
[06-integrity-authorship.md](./06-integrity-authorship.md).

## 1.4 Capability boundary — the YES/NO list

Reproduced from S1 L465–478. This is the product's constitution.

### ALLOWED

| Capability | Module |
|-----------|--------|
| Grammar correction | Writing |
| Sentence formation | Writing |
| Academic English improvement | Writing |
| Scientific terminology correction | Writing |
| Spelling | Writing |
| Data analysis | Data / Plot Studio |
| Graphs | Plot Studio |
| Statistics | Plot Studio |
| References & formatting | Literature |
| Journal preparation | Journal Preparation |

### FORBIDDEN

| Capability | Why it is banned |
|-----------|------------------|
| AI-generated research claims | Fabricates science |
| AI-generated experimental results | Fabricates data |
| AI-generated references | Fabricates citations — a research-integrity offence |
| Automatic scientific content generation | The umbrella prohibition |

Note the sharp line: the platform manipulates *the language of* science and *the presentation of*
data, but never *the content of* science. "Data analysis" is allowed because the numbers come from
the user; "experimental results" are banned because they do not.

## 1.5 Audience

Stated or strongly implied across both sources:

| Audience | Evidence |
|----------|----------|
| Research students / early-career researchers | Non-native-English scientific writing features ("Rough, non-native phrasing rebuilt into correct scientific English", L286) |
| Researchers working in *any* of 17 disciplines | "Not chemistry software. Not biology software." (L420) |
| Researchers preparing journal submissions | Journal presets, submission prep, export formats |
| Research labs | Stage 4: "research labs, supervisor dashboards" |
| Universities / institutions | Stage 4: "University accounts … institutional repositories, admin" |
| Supervisors / PIs | Stage 4: "supervisor dashboards" |

## 1.6 Discipline coverage

Seventeen disciplines (S1 L422–429):
Chemistry · Physics · Biology · Biotechnology · Medicine · Pharmacy · Agriculture · Engineering ·
Computer Science · AI / Data Science · Mathematics · Environmental Science · Psychology ·
Economics · Management · Education · Social Sciences · Humanities

**Stated model (L421):**
> Each discipline carries its own terminology, manuscript templates, statistical methods, and
> journal formats — on the same shared SCIX core.

So the platform is **one core + N discipline profiles**. A discipline profile is a first-class
data object, not a hardcoded branch. Full breakdown in
[07-disciplines-terminology.md](./07-disciplines-terminology.md).

## 1.7 Success criteria implied by the sources

Not stated as metrics, but derivable from the emphasis:

1. A non-native researcher can produce a grammatically correct, terminologically consistent,
   journal-formatted manuscript without leaving the platform.
2. Every edit in that manuscript is traceable to HUMAN or SOFTWARE.
3. A figure exported from Plot Studio passes the 12-point figure audit.
4. Any figure can be traced back to its source dataset, transformations and analysis.
5. The same tool serves a chemistry XRD dataset and a psychology Likert-scale survey.
