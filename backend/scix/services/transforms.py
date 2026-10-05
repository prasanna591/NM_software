"""The ordered, replayable transformation log.

IRREVERSIBLE (docs/08 8.6). S2 3.13 requires "Processing: Normalization -> Log
transformation" and a Trace action that returns to every intermediate state. That is a
chain, not a flag: ``normalized: true`` cannot express a log applied after the
normalization, and cannot express what the values were before it.

Two rules hold this together:

1. **seq is dense and monotonic per worksheet.** The new step's seq is
   ``worksheet.transform_seq + 1`` inside the same transaction as the write. The unique
   constraint ``uq_data_transformations_worksheet_seq`` is the backstop; a gap means the
   Parquet artefacts cannot be lined up with the chain, and Trace would lie.

2. **Every step is a pure function of (previous frame, params).** ``apply_transform``
   takes a frame and returns a frame, with no database access and no I/O. That is what
   makes ``replay`` possible: the same code path produces the same values from the base
   file, so a re-derived worksheet is identical rather than approximately identical.

Replay is not a debugging convenience here. It is how "reconstruct or at minimum navigate
to every intermediate state" is satisfied, and how a researcher confirms that the figure
on screen came from the data they uploaded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from scix.models import Column, DataTransformation, Dataset, Worksheet
from scix.models.enums import TargetKind, TransformType
from scix.services import audit as audit_log


class TransformError(ValueError):
    """A transform cannot be applied as specified.

    Raised rather than warned-and-continued: a partially applied step would leave the
    worksheet's Parquet file disagreeing with its log entry, which is precisely the
    state Trace must never produce.
    """


@dataclass
class TransformOutcome:
    worksheet: Worksheet
    transformation: DataTransformation
    row_count_before: int
    row_count_after: int
    output_columns: list[str]
    warnings: list[str]


def apply_transform(
    frame,  # pandas.DataFrame
    transform_type: TransformType,
    params: dict[str, Any],
    output_name: str | None = None,
) -> tuple[Any, list[str], list[str]]:
    """Pure. Returns (new_frame, input_columns, output_columns). No I/O, no database.

    Kept free of both by design: a pure function is testable in isolation and is the
    only way replay can be trustworthy.
    """
    import numpy as np
    import pandas as pd

    warnings: list[str] = []

    def numeric_columns() -> list[str]:
        return [
            c
            for c in frame.columns
            if pd.api.types.is_numeric_dtype(frame[c]) or c in params.get("columns", [])
        ]

    def require(names: list[str], what: str) -> None:
        missing = [n for n in names if n not in frame.columns]
        if missing:
            raise TransformError(
                f"{transform_type.value}: {what} not in worksheet: {missing}. "
                f"Available: {list(frame.columns)}"
            )

    if transform_type is TransformType.NORMALIZE:
        cols = params.get("columns") or numeric_columns()
        require(cols, "columns")
        method = params.get("method", "zscore")
        # Named columns only. Selecting by position would silently normalize the wrong
        # column after an upstream insertion or reorder.
        block = frame[cols].apply(pd.to_numeric, errors="coerce")

        if method == "zscore":
            means = block.mean(axis=0)
            stds = block.std(axis=0, ddof=1)
            zero = stds[stds == 0]
            for name in zero.index:
                warnings.append(
                    f"normalization skipped for {name!r}: zero variance, z-score undefined"
                )
            usable = [c for c in cols if stds[c] != 0]
            if usable:
                frame = frame.copy()
                frame[usable] = ((block[usable] - means[usable]) / stds[usable]).to_numpy()
        elif method == "minmax":
            mins = block.min(axis=0)
            ranges = block.max(axis=0) - mins
            const = ranges[ranges == 0]
            for name in const.index:
                warnings.append(f"min-max skipped for {name!r}: constant column")
            usable = [c for c in cols if ranges[c] != 0]
            if usable:
                frame = frame.copy()
                frame[usable] = ((block[usable] - mins[usable]) / ranges[usable]).to_numpy()
        elif method == "percent_of_control":
            control = params.get("control")
            if not control:
                raise TransformError("percent_of_control requires 'control': a column name")
            require([control], "control column")
            target = params.get("column")
            cols = [target] if target else cols
            require(cols, "columns")
            baseline = pd.to_numeric(frame[control], errors="coerce")
            frame = frame.copy()
            for c in cols:
                values = pd.to_numeric(frame[c], errors="coerce")
                frame[c] = (values / baseline.replace(0, np.nan) - 1.0) * 100.0
                warnings.append(
                    f"{c!r} expressed as percent change relative to {control!r}; "
                    f"zero denominators became missing rather than infinite"
                )
        else:
            raise TransformError(
                f"unknown normalization method {method!r}. Supported: zscore, minmax, "
                f"percent_of_control"
            )
        return frame, cols, cols

    if transform_type is TransformType.LOG:
        cols = params.get("columns") or numeric_columns()
        require(cols, "columns")
        base = float(params.get("base", 10))
        offset = float(params.get("offset", 0.0))
        frame = frame.copy()
        negatives: list[str] = []
        for c in cols:
            values = pd.to_numeric(frame[c], errors="coerce")
            mask = values <= offset
            if bool(mask.any()):
                negatives.append(c)
            # log(x + offset) on non-positive values yields -inf or NaN, and a column
            # quietly full of -inf is worse than a refused transform.
            frame[c] = np.log10(values.where(~mask) + offset)
        for c in negatives:
            warnings.append(
                f"{c!r}: {int((pd.to_numeric(frame[c], errors='coerce') <= 0).sum())} "
                f"value(s) at or below {offset} became missing; a logarithm is undefined "
                f"there. Nothing was clipped."
            )
        return frame, cols, cols

    if transform_type is TransformType.FILTER:
        column = params.get("column")
        if not column:
            raise TransformError("filter requires 'column'")
        require([column], "column")
        op = params.get("op", "notna")
        value = params.get("value")

        series = frame[column]
        if op == "notna":
            mask = series.notna()
        elif op == "isna":
            mask = series.isna()
        elif op == "eq":
            mask = series == value
        elif op == "ne":
            mask = series != value
        elif op == "gt":
            mask = pd.to_numeric(series, errors="coerce") > float(value)
        elif op == "gte":
            mask = pd.to_numeric(series, errors="coerce") >= float(value)
        elif op == "lt":
            mask = pd.to_numeric(series, errors="coerce") < float(value)
        elif op == "lte":
            mask = pd.to_numeric(series, errors="coerce") <= float(value)
        elif op == "between":
            low, high = params.get("min"), params.get("max")
            numeric = pd.to_numeric(series, errors="coerce")
            mask = numeric.between(float(low), float(high))
        elif op == "contains":
            mask = series.astype(str).str.contains(str(value), case=False, na=False)
        else:
            raise TransformError(f"unknown filter op {op!r}")

        frame = frame[mask].reset_index(drop=True)
        warnings.append(
            f"filter {column} {op} {value!r} removed {removed} row(s)"
        )
        return frame, [column], [column]

    if transform_type is TransformType.SORT:
        by = params.get("by") or []
        require(by, "by")
        ascending = params.get("ascending", True)
        if isinstance(ascending, bool):
            ascending = [ascending] * len(by)
        frame = frame.sort_values(by=by, ascending=ascending).reset_index(drop=True)
        return frame, by, by

    if transform_type is TransformType.GROUP:
        by = params.get("by") or []
        require(by, "by")
        agg = params.get("agg") or {"mean": numeric_columns()}
        if isinstance(agg, dict):
            for col in agg.values():
                require(list(col), "aggregate columns")
            grouped = frame.groupby(by, dropna=False).agg(agg)
            grouped.columns = [
                "_".join(str(p) for p in parts if p) for parts in grouped.columns.to_flat_index()
            ]
            return grouped.reset_index(), by, list(grouped.columns)
        raise TransformError("group requires 'agg' as a mapping of function -> columns")

    if transform_type is TransformType.MERGE:
        left = params.get("left_columns")
        right = params.get("right_columns")
        if not left or not right:
            raise TransformError("merge requires 'left_columns' and 'right_columns'")
        require(list(left) + list(right), "merge columns")
        frame = frame.copy()
        for c in right:
            frame[c] = pd.to_numeric(frame[c], errors="coerce")
        return frame, list(left) + list(right), list(left) + list(right)

    if transform_type is TransformType.UNIT_CONVERT:
        col = params.get("column")
        if not col:
            raise TransformError("unit_convert requires 'column'")
        require([col], "column")
        factor = float(params.get("factor", 1.0))
        frame = frame.copy()
        frame[col] = pd.to_numeric(frame[col], errors="coerce") * factor
        warnings.append(
            f"{col!r} multiplied by {factor:g}; the column unit was not rewritten -- set it "
            f"explicitly so the figure audit sees the new unit"
        )
        return frame, [col], [col]

    if transform_type is TransformType.CALCULATE_COLUMN:
        if not output_name:
            raise TransformError("calculate_column requires an output column name")
        formula = params.get("formula")
        if not formula:
            raise TransformError("calculate_column requires 'formula'")
        # Restricted evaluation. A user-supplied expression evaluated with eval() is a
        # code-execution hole in an upload-adjacent path; this allows arithmetic and a
        # fixed function set, and nothing else.
        allowed_names = set(frame.columns) | {"pi", "e", "abs", "min", "max", "sqrt", "log", "log10", "exp"}
        import ast

        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError as exc:
            raise TransformError(f"formula is not valid Python: {exc}") from exc

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id not in allowed_names:
                raise TransformError(
                    f"formula references unknown column {node.id!r}. Available: "
                    f"{sorted(set(frame.columns))}"
                )
            if isinstance(node, ast.Attribute):
                raise TransformError("formula may not use attribute access")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise TransformError("formula may not use imports")

        frame = frame.copy()
        frame[output_name] = eval(  # noqa: S307 - AST-restricted above
            compile(tree, "<formula>", "eval"), {"__builtins__": {}}, dict(frame.items())
        )
        return frame, list(frame.columns[:-1]), [output_name]

    if transform_type is TransformType.MISSING_VALUES:
        strategy = params.get("strategy", "report")
        cols = params.get("columns") or numeric_columns()
        require(cols, "columns")
        frame = frame.copy()
        if strategy == "report":
            for c in cols:
                n = int(frame[c].isna().sum())
                warnings.append(f"{c!r}: {n} missing value(s) left in place")
        elif strategy == "drop":
            frame = frame.dropna(subset=cols).reset_index(drop=True)
            warnings.append(f"dropped rows with any missing value in {cols}")
        elif strategy == "fill":
            fill = params.get("value")
            if fill is None:
                raise TransformError("missing_values strategy 'fill' requires 'value'")
            frame[cols] = frame[cols].fillna(fill)
            warnings.append(
                f"filled missing values in {cols} with {fill!r} -- this IMPUTES data; the "
                f"step is recorded so the manuscript can disclose it"
            )
        elif strategy == "interpolate":
            frame[cols] = frame[cols].interpolate(limit_direction="both")
            warnings.append(f"linearly interpolated missing values in {cols} -- IMPUTATION")
        else:
            raise TransformError(f"unknown missing_values strategy {strategy!r}")
        return frame, cols, cols

    raise TransformError(f"unhandled transform type {transform_type!r}")