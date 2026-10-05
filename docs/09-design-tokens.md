# 09 — Design Tokens & UI System

Both source documents are self-contained static pages with a complete, opinionated visual language.
Extracted from their `<style>` blocks for reuse in the product UI.

The two pages use **different but related** systems. S1 is warm/paper/manuscript; S2 is
cool/green/technical. They appear to be two applications or two contexts, not one system.

---

## 9.1 S1 — NM Scientific Research Studio

### Palette

| Token | Value | Role |
|-------|-------|------|
| `--paper` | `#f5f4f0` | Page background |
| `--paper-2` | `#ffffff` | Card / raised surface |
| `--ink` | `#1c1c1a` | Primary text; also used as the dark panel background |
| `--ink-soft` | `#55534c` | Secondary text |
| `--ink-faint` | `#8b887d` | Tertiary text, labels |
| `--rule` | `#dcd9cf` | Borders, dividers |
| `--human` | `#1f6f4a` | **Green — human-authored** |
| `--human-tint` | `#e5f0e8` | Green highlight background |
| `--assist` | `#2a4f8f` | **Blue — software-assisted** |
| `--assist-tint` | `#e6ecf8` | Blue highlight background |
| `--mark` | `#a5321f` | **Manuscript-red — corrections / track changes** |
| `--mark-tint` | `#f8e9e5` | Red highlight background |

### Semantic colour mapping

This is a **semantic three-colour system**, not a decorative palette:

| Colour | Meaning | Applied to |
|--------|---------|-----------|
| Green | Human / good / correct / accepted | Accepted edits, ✓ checks, YES rules, human authorship badges |
| Blue | Software / neutral-informational | Software authorship badges, module accents |
| Red | Correction / deletion / failure | Struck-through text, ⚠ warnings, NO rules, section eyebrows |

The CSS comments state the intent explicitly:
```css
--human:#1f6f4a;   /* green — human-authored, from the doc's own 🟢 */
--assist:#2a4f8f;  /* blue — software-assisted, from the doc's own 🔵 */
--mark:#a5321f;    /* manuscript-red — corrections / track changes */
```

**This maps directly onto the `attribution` enum.** Green = HUMAN, blue = SOFTWARE, red = a change.
Use it consistently across the entire product UI.

### Typography

| Token | Value |
|-------|-------|
| `--serif` | `"Newsreader", Georgia, serif` |
| `--mono` | `"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace` |

Loaded weights (S1 L8):
- Newsreader: 400, 500, 600, 700 + italics 400, 500 (opsz 6..72)
- JetBrains Mono: 400, 500, 600, 700

**Usage rule from the CSS:** serif for all prose, mono for all metadata, labels, navigation, buttons
and technical values. Mono is functional, not decorative — it marks anything that is an identifier
rather than an argument.

### Type scale

| Element | Size | Line height | Notes |
|---------|------|-------------|-------|
| `body` | 18px | 1.6 | |
| `h1` | `clamp(38px, 5.4vw, 66px)` | 1.04 | `max-width: 16ch`, weight 600 |
| `h1 em` | — | — | italic, weight 500, `--ink-soft` |
| `h2` | `clamp(28px, 3.4vw, 40px)` | — | weight 600, `max-width: 20ch` |
| `.hero-dek` | 20px | — | `max-width: 52ch`, `--ink-soft` |
| `.sec-dek` | 17px | — | `max-width: 58ch`, `--ink-soft` |
| `blockquote` | `clamp(24px, 3vw, 34px)` | 1.35 | weight 500 |
| `.diff-text` | 18px | 1.65 | |
| `.fcard h4` | 17px | — | weight 600 |
| `.fcard p` | 14px | 1.55 | `--ink-soft` |
| `.chip` | 13px | — | mono |
| `.pair` | 14px | — | mono |
| `footer` | 11.5px | — | mono, `--ink-faint` |

### Spacing

| Token | Value |
|-------|-------|
| `.wrap` max-width | 1180px, padding 0 56px (22px under 860px) |
| `section` padding | 80px 0 |
| `.hero` padding | 104px 0 72px |
| `.principle` padding | 64px 0 |
| `.closing` padding | 100px 0 120px |
| `.fgrid` gap | 2px (uses the border as a hairline grid — see below) |
| `.roadmap` gap | 2px |

The `2px` gap over a `--rule` background is a deliberate technique: it renders a 1px divider
between cells with zero border management. Reuse it for card grids.

### Surfaces

| Component | Treatment |
|-----------|-----------|
| `.diff-card` | `--paper-2`, 1px `--rule`, `border-radius: 6px`, `overflow: hidden`, `box-shadow: 0 1px 0 rgba(0,0,0,.02)` |
| `.pair` | `--paper-2`, 1px `--rule`, `radius: 6px`, padding 16px 20px, flex space-between |
| `.authorship` | `--ink` bg, `--paper` text, `radius: 10px`, padding 48px 52px |
| `.api-panel` | `#161513` bg, `#e9e6db` text, `radius: 6px`, mono 13px, line-height 2 |
| `.stack-layer` | `--paper-2`, 1px `--rule`, `radius: 6px`, padding 16px 22px |
| `.chip` | `--paper-2`, 1px `--rule`, `radius: 20px`, padding 7px 16px |
| `.btn` | `--paper` bg, 1px `--rule`, `radius: 3px`, padding 7px 14px, mono 12px |
| `.btn.primary` | `--human` bg/border, `#fff` text |

### Diff / track-changes treatment

The single most important visual component in S1 — it is the product's core interaction.

```css
.strike {
  color: var(--mark);
  text-decoration: line-through;
  text-decoration-thickness: 1.5px;
  background: var(--mark-tint);
  padding: 0 2px;
  border-radius: 2px;
}
.ins {
  color: var(--human);
  background: var(--human-tint);
  padding: 0 2px;
  border-radius: 2px;
}
::selection { background: var(--mark-tint); }
```

Deletions: red text, red-tint background, 1.5px strike. Insertions: green text, green-tint
background. Both with 2px horizontal padding so the highlight does not touch the glyph.

**Implement this component once and reuse it everywhere** — suggestion cards, version diffs,
document history, reviewer comments.

### Authorship panel (dark)

| Element | Value |
|---------|-------|
| Background | `--ink` `#1c1c1a` |
| Title | `#c9c6ba`, mono 13px, `letter-spacing: .06em` |
| Status text | `#9fd8b4`, mono 12.5px |
| Status dot | `#4fd88a`, 9px, `box-shadow: 0 0 0 4px rgba(79,216,138,.18)` |
| `.who.human` | bg `rgba(79,216,138,.16)`, text `#8be5ac` |
| `.who.assist` | bg `rgba(122,166,255,.16)`, text `#9db9ff` |
| Row divider | `1px solid rgba(255,255,255,.1)` |
| Row text | 15px |

The glowing dot + `HUMAN AUTHORSHIP MODE — ENABLED` is a **status indicator**, styled to be
read as system state. Reproduce it as a persistent element in the product header.

### Other components

```css
.checker-col li::before { content: "✓ "; color: var(--human); }
.diff-label  { font: 11px mono; letter-spacing: .06em; color: var(--ink-faint); }
.sec-eyebrow { font: 12px mono;  letter-spacing: .04em; color: var(--ink-faint); }
.hero-eyebrow{ font: 12.5px mono; color: var(--mark); }
.hero-note   { border-left: 2px solid var(--mark); padding-left: 16px; }
```

### Responsive

| Breakpoint | Change |
|-----------|--------|
| ≤900px | `.fgrid` → 2 columns; `.roadmap` → 2 columns |
| ≤860px | `.wrap` padding → 22px |
| ≤760px | `.navlinks` hidden |
| ≤700px | `.pairs` → 1 column; `.closing .rules` → 1 column; `.authorship` padding 32px 26px |
| ≤640px | `.auth-rows` → 1 column |
| ≤600px | `.fgrid` → 1 column |
| ≤560px | `.roadmap` → 1 column; `.checker-grid` → 1 column |
| ≤960px | `.checker-grid` → 2 columns |

### Motion

`html { scroll-behavior: smooth; }` only. No transitions, no animations. The product is meant to
feel like a document, not an app.

---

## 9.2 S2 — SCIX Plot Studio

### Palette

| Token | Value | Role |
|-------|-------|------|
| `--paper` | `#eef2f0` | Page background |
| `--paper-line` | `rgba(23,58,54,0.09)` | Grid lines |
| `--ink` | `#17322c` | Primary text; dark panel background |
| `--ink-soft` | `#3f5c54` | Secondary text |
| `--ink-faint` | `#6f8a82` | Tertiary text |
| `--rule` | `#c3d1cb` | Borders |
| `--accent` | `#1f6f5c` | Primary accent (teal-green) |
| `--accent-soft` | `#dcebe4` | Accent tint |
| `--accent-2` | `#a8572c` | Secondary accent (rust — warnings) |
| `--card` | `#f7faf8` | Card surface |
| `--serif` | `"Source Serif 4", Georgia, serif` |
| `--mono` | `"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace` |

### Signature background

```css
background:
  linear-gradient(var(--paper-line) 1px, transparent 1px) 0 0/100% 32px,
  linear-gradient(90deg, var(--paper-line) 1px, transparent 1px) 0 0/32px 100%,
  var(--paper);
```

A 32px graph-paper grid. Appropriate for a plotting tool — the UI sits on graph paper.

### Type scale

| Element | Value |
|---------|-------|
| `body` | 17px / 1.65 |
| `.hero h1` | 56px / 1.02, weight 700, `max-width: 14ch` |
| `.dek` | 19px, `max-width: 56ch` |
| `h2` | 28px, weight 600 |
| `.sec-num` | 14px mono, `--accent` |
| `.sec-sub` | 16px, `max-width: 62ch` |
| `p` | `max-width: 66ch` |
| `.panel` | 12.5px mono, `line-height: 1.7`, `white-space: pre` |
| `.disc-card` h4 | 15px |
| `.disc-card` ul | 13.5px |
| `.pillar` h4 | 16px |
| `.pillar` p | 13.5px |
| `.toc-list a` | 12.5px mono |
| `footer` | 12px mono |

### Components

```css
.shell {
  display: grid;
  grid-template-columns: 300px minmax(0,1fr);
  max-width: 1320px;
  margin: 0 auto;
}
nav.toc {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  border-right: 1px solid var(--rule);
}
.toc-list a {
  border-left: 2px solid transparent;
  border-radius: 2px;
  padding: 6px 10px 6px 12px;
}
.toc-list a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: var(--accent-soft);
  font-weight: 600;
}
```

The sticky sidebar + scroll-spy is the S2 navigation model — and it maps directly onto the
**Plot Studio three-pane layout** (§01): the left pane is the project tree, not a TOC, but the
sticky behaviour carries over.

### The `.panel` component

```css
.panel {
  background: var(--card);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 18px 20px;
  font-family: var(--mono);
  font-size: 12.5px;
  line-height: 1.7;
  overflow-x: auto;
  white-space: pre;
}
```

Used for every wireframe, schema listing and API diagram. `white-space: pre` preserves ASCII
alignment. The source comment justifies the mono choice: *"genuine interface mockups & schema, so
monospace is functional not decorative."*

**This is a documentation component, not a product component** — but the ASCII wireframes in S2
are effectively the Plot Studio's layout specification and should be reproduced in the product's
own design docs.

### Check list

```css
.check-list li::before      { content: "✓  "; color: var(--accent); }
.check-list li.warn::before { content: "⚠  "; color: var(--accent-2); }
.check-list li.warn         { color: var(--ink); }
```

Pass = accent green, warn = `--accent-2` rust. Used by the §12 figure audit. Direct mapping to
`figure_audits` result states.

### Stack / architecture rows

```css
.stack-row        { border: 1px solid var(--rule); background: var(--card); text-align: center; }
.stack-row + .stack-row { border-top: none; }   /* stacked cells share borders */
.stack-row.head   { background: var(--ink); color: var(--paper); font-weight: 600; }
```

### Pipeline chips

```css
.pipeline .step {
  padding: 9px 16px;
  border: 1px solid var(--ink);
  border-radius: 3px;
  background: var(--card);
}
.pipeline .arrow { padding: 0 10px; color: var(--ink-faint); }
```

Bordered chips separated by arrows — the 7-stage pipeline. Reusable as a progress indicator.

### Responsive

| Breakpoint | Change |
|-----------|--------|
| ≤980px | `.shell` → single column; `nav.toc` static, `height: auto`, bottom border; `.grid2`/`.grid3`/`.pillars` → 1 column; `.hero` padding 56px 24px 40px; `section` padding 40px 24px; `h1` → 38px |

One breakpoint only. The source is desktop-first — correct for a scientific plotting tool.

### Client-side behaviour

~12 lines of vanilla JS scroll-spy (`S2 L978–990`): no framework, no dependencies.

```js
const pos = window.scrollY + 120;
sections.forEach((sec, i) => { if (sec && sec.offsetTop <= pos) idx = i; });
```

Passive scroll listener, `offsetTop` comparison, 120px offset. The 120px accounts for a sticky
header. Copy as-is for the Plot Studio project tree.

---

## 9.3 Reconciling the two systems

| Aspect | S1 | S2 | Recommendation |
|--------|----|----|----------------|
| Serif | Newsreader | Source Serif 4 | Pick one. Both are high-quality optical serifs. |
| Mono | JetBrains Mono | JetBrains Mono | **Already identical** — keep |
| Base size | 18px | 17px | 18px for reading-heavy UI, 17px for dense tools |
| Green (human) | `#1f6f4a` | `#1f6f5c` | Very close. Unify. |
| Red (mark) | `#a5321f` | `#a8572c` | Different roles: correction vs warning. Keep separate. |
| Blue (software) | `#2a4f8f` | — | S2 has no software-blue. Needed for attribution parity. |
| Layout | Single column, sticky topbar | Sticky sidebar + main | Product needs the sidebar (Plot Studio is a 3-pane app) |
| Grid background | Flat paper | 32px graph paper | Graph paper fits Plot Studio; flat fits Writing |
| Breakpoints | 8 | 1 | Adopt a middle set (~6) |

### Shared semantic tokens for the product

```css
:root {
  /* Attribution — from S1, product invariant */
  --human:        #1f6f4a;   --human-tint:  #e5f0e8;
  --assist:       #2a4f8f;   --assist-tint: #e6ecf8;
  --mark:         #a5321f;   --mark-tint:   #f8e9e5;

  /* Surfaces — S2 */
  --paper:        #eef2f0;   --card:        #f7faf8;
  --rule:         #c3d1cb;

  /* Type */
  --serif: "Newsreader", Georgia, serif;
  --mono:  "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
}
```

The attribution trio is non-negotiable and must not be restyled per module — it is the product's
core claim rendered as colour.

## 9.4 Component inventory to build

| Component | Source | Priority |
|-----------|--------|----------|
| **Diff / track-changes block** | S1 `.diff-card` | **Critical** — the core interaction |
| **Suggestion action bar** (Accept/Edit/Reject) | S1 `.diff-actions` | **Critical** |
| **Authorship badge** (HUMAN / SOFTWARE) | S1 `.who` | **Critical** |
| **Authorship status indicator** | S1 `.authorship-toggle` | **Critical** |
| **Check list** (✓ / ⚠) | S2 `.check-list` | High — figure audit, checker |
| **Consistency pair** (bad → good) | S1 `.pair` | High — terminology/consistency |
| **Card grid** (2px-gap hairline) | S1 `.fgrid`, `.roadmap` | High |
| **Pipeline stepper** | S2 `.pipeline` | High — Plot Studio progress |
| **Stack / architecture rows** | S2 `.stack` | Medium — internal docs |
| **Property panel** | S2 §01/§05 wireframes | **Critical** — Plot Studio right panel |
| **Three-pane shell** | S2 §01 | **Critical** — Plot Studio frame |
| **Project tree** | S2 §01 left pane | **Critical** |
| **Status bar** | S2 §01 | High — live provenance |
| **Menu bar** | S2 §01 | High |
| **Sticky sidebar + scroll-spy** | S2 `nav.toc` | High |
| **Chip / tag** | S1 `.chip` | Medium |
| **Wireframe panel** (mono, `white-space: pre`) | S2 `.panel` | Medium — docs only |
| **Terminology checkbox list** | S2 `.disc-card` | Low — content presentation |
