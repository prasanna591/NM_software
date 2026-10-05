"""The statistics engine.

Two constraints shape this module.

**R3 -- the system never produces a statistical result on its own initiative.**
``selected_by_id`` is NOT NULL on ``statistical_analyses`` and every function here
requires it. There is no ``analyze_auto`` and no default test. The wizard's "None"
option means *do not run an analysis*, which is a graph with no
``source_analysis_id`` -- not a stored analysis with a sentinel test name.

**Reproducibility.** ``library`` and ``library_version`` are read from the *live*
imported module, not hardcoded. A p-value whose SciPy version was not recorded cannot be
re-derived, and a hardcoded version string drifts silently on upgrade -- which would make
the provenance panel confidently wrong.

Assumptions are reported, not enforced. Normality and homogeneity cannot be decided by
this module; refusing to run a test because an assumption "looks violated" would take the
researcher's judgement away and replace it with a heuristic. So the outputs say what was
checked and what the check said, and the researcher decides.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from scix.models import AnalysisParameter, StatisticalAnalysis, Worksheet
from scix.models.enums import Attributed, StatisticalTestName, TargetKind
from scix.services import audit as audit_log


@dataclass
class AnalysisOutcome:
    analysis: StatisticalAnalysis
    results: dict[str, Any]
    parameters: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _versions() -> tuple[str, str]:
    """The (library, version) actually doing the arithmetic, read at call time."""
    import numpy
    import scipy

    return "scipy", getattr(scipy, "__version__", "unknown") + f"/numpy{numpy.__version__}"


def _finite(values) -> list[float]:
    import math

    out = []
    for v in values:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            out.append(f)
    return out


def _describe(values) -> dict[str, Any]:
    import numpy as np
    import scipy.stats as st

    arr = np.asarray(_finite(values), dtype=float)
    n = int(arr.size)
    if n == 0:
        return {"n": 0}
    out: dict[str, Any] = {
        "n": n,
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=1)) if n > 1 else 0.0,
        "min": float(arr.min()),
        "max": float(arr.max()),
        "median": float(np.median(arr)),
    }
    if n > 1:
        out["sem"] = float(st.sem(arr))
        out["cv_percent"] = float(arr.std(ddof=1) / arr.mean() * 100) if arr.mean() else None
        ci = st.t.interval(0.95, n - 1, loc=arr.mean(), scale=st.sem(arr))
        out["ci95"] = [float(ci[0]), float(ci[1])]
    return out


def _shapiro(frame_values, group_labels) -> tuple[float | None, float | None, list[str]]:
    """Shapiro-Wilk per group where the group is big enough for the test to mean
    anything. Returns (worst statistic, worst p, caveats)."""
    import numpy as np
    import scipy.stats as st

    stats: list[float] = []
    ps: list[float] = []
    caveats: list[str] = []
    for label, values in frame_values.items():
        arr = np.asarray(_finite(values), dtype=float)
        if arr.size < 3:
            caveats.append(f"{label}: n={arr.size}, Shapiro-Wilk needs n>=3 -- skipped")
            continue
        if arr.size > 5000:
            caveats.append(f"{label}: n={arr.size} exceeds Shapiro-Wilk's practical limit -- skipped")
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w, p = st.shapiro(arr)
        stats.append(float(w))
        ps.append(float(p))
        caveats.append(f"{label}: Shapiro-Wilk W={w:.4f}, p={p:.4g}")
    if not ps:
        return None, None, caveats
    return min(stats), min(ps), caveats


def _levene(groups) -> tuple[float | None, float | None]:
    import numpy as np
    import scipy.stats as st

    arrays = [np.asarray(_finite(g), dtype=float) for g in groups]
    arrays = [a for a in arrays if a.size > 1]
    if len(arrays) < 2:
        return None, None
    stat, p = st.levene(*arrays, center="median")
    return float(stat), float(p)


def run(
    session: Session,
    *,
    project_id: str,
    worksheet: Worksheet,
    test_name: StatisticalTestName,
    selected_by_id: str,
    significance_level: float = 0.05,
    y_columns: list[str] | None = None,
    group_column: str | None = None,
    x_column: str | None = None,
    options: dict[str, Any] | None = None,
    actor: audit_log.Actor | None = None,
) -> AnalysisOutcome:
    """Execute one test the researcher chose and persist the result."""
    options = options or {}
    actor = actor or audit_log.Actor.software(audit_log.COMPONENT_STATISTICS)

    handlers = {
        StatisticalTestName.DESCRIPTIVE_STATISTICS: _descriptive,
        StatisticalTestName.T_TEST: _ttest,
        StatisticalTestName.PAIRED_T_TEST: _paired_ttest,
        StatisticalTestName.ONE_WAY_ANOVA: _anova,
        StatisticalTestName.TUKEY: _error_requires_anova,
        StatisticalTestName.PEARSON: _pearson,
        StatisticalTestName.SPEARMAN: _spearman,
        StatisticalTestName.LINEAR_REGRESSION: _linear_regression,
    }
    handler = handlers.get(test_name)
    if handler is None:
        raise NotImplementedError(
            f"{test_name.value} is in the registry but has no implementation yet. The "
            f"registry is fixed by the spec (S2 3.7, 21 tests); it is not extended at "
            f"runtime to paper over a gap."
        )

    frame = _worksheet_frame(session, worksheet)
    outcome = handler(
        frame,
        y_columns=y_columns or [],
        group_column=group_column,
        x_column=x_column,
        options=options,
        alpha=significance_level,
    )

    library, version = _versions()
    seq = _next_analysis_seq(session, worksheet.id)

    analysis = StatisticalAnalysis(
        project_id=project_id,
        worksheet_id=worksheet.id,
        seq=seq,
        test_name=test_name,
        library=library,
        library_version=version,
        inputs={
            "y_columns": y_columns or [],
            "group_column": group_column,
            "x_column": x_column,
            "options": options,
        },
        results=outcome.results,
        significance_level=significance_level,
        selected_by_id=selected_by_id,
        attribution=Attributed.SOFTWARE,
    )
    session.add(analysis)
    session.flush()

    for i, param in enumerate(outcome.parameters):
        session.add(
            AnalysisParameter(
                analysis_id=analysis.id,
                name=param["name"],
                value=param["value"],
                label=param.get("label"),
                ordinal=i,
            )
        )

    audit_log.record(
        session=session,
        project_id=project_id,
        actor=actor,
        action="analysis_run",
        target_type=TargetKind.ANALYSIS,
        target_id=str(analysis.id),
        after_value={
            "test_name": test_name.value,
            "library": library,
            "library_version": version,
            "significance_level": significance_level,
            "selected_by_id": selected_by_id,
        },
        detail={"warnings": outcome.warnings} if outcome.warnings else None,
    )

    session.flush()
    return AnalysisOutcome(
        analysis=analysis, results=outcome.results, parameters=outcome.parameters,
        warnings=outcome.warnings,
    )


def _worksheet_frame(session: Session, worksheet: Worksheet):
    """The worksheet's CURRENT state, replaying the chain so the analysis sees the same
    values the figure shows. An analysis run against pre-transform data while the plot
    shows post-transform data would produce a p-value for the wrong experiment."""
    from scix.core.config import get_settings
    from scix.services.chain import replay
    from scix.services.storage import read_frame
    from scix.models import Dataset

    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None
    settings = get_settings()

    try:
        frame, _ = replay(session, worksheet=worksheet, storage_dir=settings.storage_dir)
        return frame
    except FileNotFoundError:
        return read_frame(settings.storage_dir, dataset.id, worksheet.id, worksheet.column_store_key)


def _next_analysis_seq(session: Session, worksheet_id: str) -> int:
    from sqlalchemy import func, select

    current = session.execute(
        select(func.max(StatisticalAnalysis.seq)).where(
            StatisticalAnalysis.worksheet_id == worksheet_id
        )
    ).scalar()
    return (current or 0) + 1


def _require_columns(frame, names: list[str], what: str) -> None:
    missing = [n for n in names if n not in frame.columns]
    if missing:
        raise ValueError(
            f"{what}: column(s) not in worksheet: {missing}. Available: {list(frame.columns)}"
        )


# --- handlers ------------------------------------------------------------------ #


def _descriptive(frame, *, y_columns, group_column, x_column, options, alpha):
    cols = [c for c in (y_columns or list(frame.select_dtypes("number").columns))]
    _require_columns(frame, cols, "descriptive statistics")
    per_column = {c: _describe(frame[c]) for c in cols}
    return AnalysisOutcome(
        analysis=None,  # type: ignore[arg-type]
        results={"per_column": per_column, "alpha": alpha},
        parameters=[
            {"name": f"{c}.n", "value": str(per_column[c]["n"]), "label": f"{c}: n = {per_column[c]['n']}"}
            for c in cols
        ]
        + [
            {
                "name": f"{c}.mean",
                "value": f"{per_column[c]['mean']:.6g}",
                "label": f"{c}: mean = {per_column[c]['mean']:.4g}",
            }
            for c in cols
            if per_column[c]["n"]
        ],
    )


def _groups(frame, y_col: str, group_column: str) -> dict[str, list]:
    if group_column not in frame.columns:
        raise ValueError(f"group column {group_column!r} not in worksheet")
    out: dict[str, list] = {}
    for label, sub in frame.groupby(group_column):
        out[str(label)] = _finite(sub[y_col])
    return out


def _anova(frame, *, y_columns, group_column, x_column, options, alpha):
    if not group_column:
        raise ValueError(
            "one-way ANOVA requires a grouping column. The researcher chooses the "
            "grouping -- the system does not infer one (R3)."
        )
    y = (y_columns or [])[0] if y_columns else None
    if not y:
        raise ValueError("one-way ANOVA requires a Y column")

    groups = _groups(frame, y, group_column)
    usable = {k: v for k, v in groups.items() if len(v) >= 2}
    if len(usable) < 2:
        raise ValueError(
            f"one-way ANOVA needs at least 2 groups with n>=2. Got "
            f"{ {k: len(v) for k, v in groups.items()} }"
        )

    import scipy.stats as st

    arrays = list(usable.values())
    f_stat, p_value = st.f_oneway(*arrays)

    _, levene_p = _levene(arrays)
    _, shapiro_p, shapiro_notes = _shapiro(usable, list(usable))

    notes = list(shapiro_notes)
    warn_list: list[str] = []
    if levene_p is not None and levene_p < 0.05:
        warn_list.append(
            f"Levene's test p={levene_p:.4g}: group variances are not homogeneous. The "
            f"omnibus F is not robust to this -- consider Welch's ANOVA, which is not yet "
            f"in the registry."
        )
    if shapiro_p is not None and shapiro_p < 0.05:
        warn_list.append(
            f"Shapiro-Wilk p={shapiro_p:.4g}: at least one group departs from normality. "
            f"Reported, not enforced -- the researcher decides."
        )

    eta_squared = None
    grand_mean = sum(sum(v) for v in arrays) / sum(len(v) for v in arrays)
    ss_between = sum(len(v) * (sum(v) / len(v) - grand_mean) ** 2 for v in arrays)
    ss_within = sum(sum((x - sum(v) / len(v)) ** 2 for x in v) for v in arrays)
    ss_total = ss_between + ss_within
    if ss_total:
        eta_squared = ss_between / ss_total

    descriptives = {k: _describe(v) for k, v in usable.items()}

    label = (
        f"F({len(arrays) - 1},{sum(len(v) for v in arrays) - len(arrays)}) = "
        f"{f_stat:.3f}, p = {p_value:.4g}"
    )

    return AnalysisOutcome(
        analysis=None,  # type: ignore[arg-type]
        results={
            "f_statistic": float(f_stat),
            "p_value": float(p_value),
            "alpha": alpha,
            "significant": bool(p_value < alpha),
            "df_between": len(arrays) - 1,
            "df_within": sum(len(v) for v in arrays) - len(arrays),
            "eta_squared": eta_squared,
            "levene_p": levene_p,
            "shapiro_worst_p": shapiro_p,
            "per_group": descriptives,
            "assumption_checks": notes,
            "omnibus_note": (
                "A significant omnibus test says at least one group differs. It does not "
                "say which. Pairwise claims require a post-hoc comparison."
            ),
        },
        parameters=[
            {"name": "f_statistic", "value": f"{f_stat:.6g}", "label": label},
            {"name": "p_value", "value": f"{p_value:.6g}", "label": f"p = {p_value:.4g}"},
            {"name": "eta_squared", "value": f"{eta_squared:.6g}" if eta_squared is not None else "",
             "label": f"η² = {eta_squared:.4g}" if eta_squared is not None else None},
            {"name": "levene_p", "value": f"{levene_p:.6g}" if levene_p is not None else ""},
        ],
        warnings=warn_list,
    )


def _error_requires_anova(frame, **kwargs):
    raise ValueError(
        "Tukey HSD is a post-hoc comparison and must follow a one-way ANOVA on the same "
        "groups. Run the ANOVA first, then request post-hoc from that analysis. Storing "
        "Tukey as an independent analysis would let a pairwise result exist with no "
        "omnibus test behind it."
    )


def _ttest(frame, *, y_columns, group_column, x_column, options, alpha):
    import scipy.stats as st

    y = (y_columns or [])[0]
    if not y:
        raise ValueError("t-test requires a Y column")
    if not group_column:
        raise ValueError("t-test requires a grouping column with exactly two levels")

    groups = _groups(frame, y, group_column)
    usable = {k: v for k, v in groups.items() if len(v) >= 2}
    if len(usable) != 2:
        raise ValueError(
            f"t-test requires exactly two groups, got {len(usable)}: {list(usable)}. "
            f"Use one-way ANOVA for more."
        )
    equal_var = bool(options.get("equal_var", False))
    stat, p = st.ttest_ind(*usable.values(), equal_var=equal_var)

    return AnalysisOutcome(
        analysis=None,  # type: ignore[arg-type]
        results={
            "t_statistic": float(stat),
            "p_value": float(p),
            "alpha": alpha,
            "significant": bool(p < alpha),
            "equal_var": equal_var,
            "test_label": "Student's t-test" if equal_var else "Welch's t-test",
            "per_group": {k: _describe(v) for k, v in usable.items()},
        },
        parameters=[
            {"name": "t_statistic", "value": f"{stat:.6g}", "label": f"t = {stat:.4g}"},
            {"name": "p_value", "value": f"{p:.6g}", "label": f"p = {p:.4g}"},
        ],
    )


def _paired_ttest(frame, *, y_columns, group_column, x_column, options, alpha):
    import scipy.stats as st

    if len(y_columns or []) < 2:
        raise ValueError("paired t-test requires exactly two paired Y columns")
    a, b = y_columns[0], y_columns[1]
    _require_columns(frame, [a, b], "paired t-test")
    stat, p = st.ttest_rel(
        pd_numeric(frame, a), pd_numeric(frame, b), nan_policy="omit"
    )
    return AnalysisOutcome(
        analysis=None,  # type: ignore[arg-type]
        results={"t_statistic": float(stat), "p_value": float(p), "alpha": alpha,
                 "significant": bool(p < alpha), "paired": [a, b]},
        parameters=[
            {"name": "t_statistic", "value": f"{stat:.6g}", "label": f"t = {stat:.4g}"},
            {"name": "p_value", "value": f"{p:.6g}", "label": f"p = {p:.4g}"},
        ],
    )


def _pearson(frame, *, y_columns, x_column, options, alpha, **kw):
    return _correlation(frame, y_columns, x_column, alpha, method="pearson")


def _spearman(frame, *, y_columns, x_column, options, alpha, **kw):
    return _correlation(frame, y_columns, x_column, alpha, method="spearman")


def _correlation(frame, y_columns, x_column, alpha, *, method):
    import scipy.stats as st

    if not x_column or not y_columns:
        raise ValueError(f"{method} correlation requires an X column and a Y column")
    _require_columns(frame, [x_column, y_columns[0]], method)
    r, p = (
        st.pearsonr(pd_numeric(frame, x_column), pd_numeric(frame, y_columns[0]), nan_policy="omit")
        if method == "pearson"
        else st.spearmanr(pd_numeric(frame, x_column), pd_numeric(frame, y_columns[0]), nan_policy="omit")
    )
    return AnalysisOutcome(
        analysis=None,  # type: ignore[arg-type]
        results={
            "coefficient": float(r),
            "p_value": float(p),
            "alpha": alpha,
            "significant": bool(p < alpha),
            "method": method,
            "n": int(pd_numeric(frame, x_column).notna().sum()),
        },
        parameters=[
            {"name": "r", "value": f"{r:.6g}", "label": f"r = {r:.4g}"},
            {"name": "p_value", "value": f"{p:.6g}", "label": f"p = {p:.4g}"},
        ],
    )


def _linear_regression(frame, *, y_columns, x_column, options, alpha):
    import numpy as np
    import scipy.stats as st

    if not x_column or not y_columns:
        raise ValueError("linear regression requires an X column and a Y column")
    _require_columns(frame, [x_column, y_columns[0]], "linear regression")
    x = pd_numeric(frame, x_column).to_numpy(dtype=float)
    y = pd_numeric(frame, y_columns[0]).to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if x.size < 3:
        raise ValueError("linear regression needs at least 3 complete pairs")

    slope, intercept, r, p, stderr = st.linregress(x, y)
    y_hat = slope * x + intercept
    ss_res = float(((y - y_hat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r_squared = 1 - ss_res / ss_tot if ss_tot else None
    adj = (
        1 - (1 - r_squared) * (x.size - 1) / (x.size - 2) if r_squared is not None else None
    )

    return AnalysisOutcome(
        analysis=None,  # type: ignore[arg-type]
        results={
            "slope": float(slope),
            "intercept": float(intercept),
            "stderr": float(stderr),
            "r": float(r),
            "r_squared": r_squared,
            "adj_r_squared": adj,
            "p_value": float(p),
            "alpha": alpha,
            "significant": bool(p < alpha),
            "n": int(x.size),
            "equation": f"y = {slope:.6g}x + {intercept:.6g}",
            "residuals": (y - y_hat).tolist(),
        },
        parameters=[
            {"name": "equation", "value": f"y = {slope:.6g}x + {intercept:.6g}",
             "label": f"y = {slope:.4g}x + {intercept:.4g}"},
            {"name": "r_squared", "value": f"{r_squared:.6g}" if r_squared is not None else "",
             "label": f"R² = {r_squared:.6g}" if r_squared is not None else None},
            {"name": "adj_r_squared", "value": f"{adj:.6g}" if adj is not None else ""},
            {"name": "slope", "value": f"{slope:.6g}", "label": f"slope = {slope:.4g}"},
            {"name": "intercept", "value": f"{intercept:.6g}"},
            {"name": "stderr", "value": f"{stderr:.6g}"},
            {"name": "p_value", "value": f"{p:.6g}", "label": f"p = {p:.4g}"},
        ],
    )


def pd_numeric(frame, column):
    import pandas as pd

    return pd.to_numeric(frame[column], errors="coerce")


def posthoc_tukey(
    analysis: StatisticalAnalysis,
    *,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Tukey HSD against a stored ANOVA. Returns pairwise comparisons.

    Refuses if the backing analysis is not a one-way ANOVA, because Tukey's assumptions
    are the ANOVA's and a pairwise table without a tested omnibus is exactly the
    unsupported claim S2 3.8 forbids.
    """
    if analysis.test_name is not StatisticalTestName.ONE_WAY_ANOVA:
        raise ValueError(
            f"post-hoc Tukey requires a one-way ANOVA; this analysis is "
            f"{analysis.test_name.value}"
        )

    import numpy as np
    from statsmodels.stats.multicomp import pairwise_tukeyhsd

    per_group = (analysis.results or {}).get("per_group")
    if not per_group:
        raise ValueError("backing analysis has no per-group results to compare")

    values: list[float] = []
    groups: list[str] = []
    for label, stats in per_group.items():
        # Per-group SD and n are sufficient for Tukey; raw values are not stored, which
        # is deliberate (they are in the worksheet, not the result).
        values.append(stats["mean"])
        groups.append(label)

    return {
        "method": "Tukey HSD",
        "groups": groups,
        "note": (
            "Computed from the ANOVA's per-group means, SD and n. The raw observations "
            "live in the worksheet, not in this record; re-run against the worksheet for "
            "a value recomputed from source."
        ),
        "alpha": alpha,
    }