# ADR 0003 — Rendering authority: Matplotlib owns output, Plotly owns preview

**Status:** Accepted
**Date:** 2026-10-03
**Closes:** Q4 (docs/10-open-questions.md)
**Impact:** Graph Editor, export engine, §13 reproducibility

---

## Context

S2 §15 places both **Matplotlib** and **Plotly** in the visualisation layer with no split point
defined. `docs/09-design-tokens.md` and `docs/03-plot-studio.md` both assume interactive editing in
the browser. §13 requires figures to be traceable and reproducible; journal presets (§10) require
exact width/height/DPI/font/file-format compliance.

Three architectures were considered:

| Option | Plotly | Matplotlib | Problem |
|--------|--------|-----------|---------|
| A. Dual | interactive canvas | static export | two rendering paths that can disagree |
| B. Server-only | — | everything | slow interactive editing; Plotly is dead weight in the stack |
| C. Client-only | everything | — | no deterministic export path |

## Decision

**Matplotlib is the single authority for anything that leaves the system. Plotly is a preview
surface only.**

```
graph_spec (canonical, in Postgres)
        │
        ├─► Plotly  ──► browser preview          (interactive, fast, approximate)
        │
        └─► Matplotlib ──► PNG / TIFF / SVG / PDF / EPS   (authoritative, exact)
                             │
                             └─► embedded in DOCX / PPTX / LaTeX
```

The `graph_spec` in `graphs` + `graph_series` + `graph_axes` is the **single source of truth**. Both
renderers are pure functions of it. Neither renderer holds state.

## Rationale

1. **Reproducibility requires determinism.** §13 says a figure is version-pinned. Matplotlib with
   pinned fonts, pinned DPI and a pinned version produces byte-stable output for a given spec.
   A browser-rendered Plotly figure depends on the viewer's browser, font availability and JS
   version. It cannot satisfy §13.

2. **Journal compliance is exact.** §10 requires specific width, height, resolution, file format and
   font. Matplotlib is directly parameterised by all of them (`figsize` in inches = mm/25.4,
   `dpi`, `savefig(format=...)`, `font.family`). Plotly's export is a client-side rasteriser with
   its own font model.

3. **Server-side means no dependency on the client.** A reviewer opening a colleague's figure link
   sees the same thing.

4. **The export engine already needs Matplotlib.** S2 §15 puts it in the pipeline. Adding Plotly as
   a *second authority* is what creates risk, not having Plotly at all.

## Consequences

**Gains**
- One authority for output — export cannot disagree with itself
- Deterministic, version-pinned, reproducible figures (§13 satisfied)
- Exact journal-spec compliance (§10)
- Figures render identically regardless of viewer

**Costs — accepted**
- **Preview and export can differ visually.** Accepted and mitigated by visual regression tests on
  export fixtures (docs/11-build-strategy.md §11.12 risk 9).
- Browser interaction latency. Mitigated: preview is Plotly and fast; the authoritative render
  happens on export, asynchronously.
- Font availability differs between browser and server. Server fonts are pinned in the container;
  the client receives the font list and renders with fallbacks. Documented as a known preview
  limitation.

## Rules

| Rule | Reason |
|------|--------|
| Matplotlib uses the `Agg` backend — never an interactive one | headless worker |
| Fonts are pinned and bundled in the container | journal compliance |
| `figsize` is derived from `width_mm / 25.4`, `height_mm / 25.4` | §09 example: 85 × 65 mm |
| `dpi` defaults to **600** | §09 |
| A render records the Matplotlib version in the export row | §13 `Version: v1.4` analogue |
| Plotly output is never written to `exports` | it is preview only |

## Consequences for the Phase 1 slice

The vertical slice (docs/11-build-strategy.md §11.4) exports **server-side Matplotlib at 600 DPI**.
Plotly is wired into the preview surface in a later phase, once `graph_spec` is stable. This avoids
building the preview before the spec it renders has stopped changing.
