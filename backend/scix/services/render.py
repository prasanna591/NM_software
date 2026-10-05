"""Graph construction and the render spec.

ADR 0003: the graph row is the canonical spec. Plotly draws the preview in the browser;
Matplotlib renders the authoritative output. Neither holds state, and both consume the
``RenderSpec`` produced here -- so a preview and an export cannot disagree about what was
plotted, because they are reading the same structure.

This is why the render spec carries actual values rather than just column ids. A
Plotly trace needs coordinates; resolving ids to values once, here, means a preview
cannot fail because a column was renamed between the spec being built and the browser
requesting it.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from scix.models import Column, Dataset, Graph, GraphAxis, GraphSeries, Worksheet
from scix.models.enums import AxisScale, ErrorBasis, GraphType
from scix.services.chain import replay


def build_graph_spec(
    session: Session,
    *,
    graph: Graph,
    max_points: int = 5000,
) -> dict[str, Any]:
    """Resolve a graph into concrete plottable series.

    Returns the dict consumed by :class:`scix.schemas.api.RenderSpec`.
    """
    worksheet = _worksheet_for(session, graph)
    frame = None
    if worksheet is not None:
        try:
            frame, _ = replay(session, worksheet=worksheet, storage_dir=_storage_dir())
        except FileNotFoundError:
            frame = None

    by_id = {c.id: c for c in worksheet.columns} if worksheet else {}

    series_out: list[dict[str, Any]] = []
    for series in sorted(graph.series, key=lambda s: s.ordinal):
        y_col = by_id.get(series.y_column_id) if series.y_column_id else None
        x_col = by_id.get(series.x_column_id) if series.x_column_id else None
        err_col = by_id.get(series.error_column_id) if series.error_column_id else None

        x_values, y_values = _extract(frame, x_col, y_col, max_points)
        if err_col is not None and frame is not None and err_col.name in frame.columns:
            series_out.append(
                {
                    "name": series.name,
                    "x": x_values,
                    "y": y_values,
                    "color": series.color,
                    "line_style": series.line_style,
                    "symbol": series.symbol,
                    "error_y": _numeric_list(frame[err_col.name].head(max_points)),
                    "error_basis": series.error_basis.value,
                }
            )
        else:
            series_out.append(
                {
                    "name": series.name,
                    "x": x_values,
                    "y": y_values,
                    "color": series.color,
                    "line_style": series.line_style,
                    "symbol": series.symbol,
                    "error_y": None,
                    "error_basis": series.error_basis.value,
                }
            )

    axes = {a.axis: a for a in graph.axes}
    return {
        "graph_id": str(graph.id),
        "graph_type": graph.graph_type.value,
        "width_mm": graph.width_mm,
        "height_mm": graph.height_mm,
        "dpi": graph.dpi,
        "background": graph.background,
        "series": series_out,
        "x_axis": _axis_out(axes.get("x")),
        "y_axis": _axis_out(axes.get("y")),
        "legend": len(series_out) > 1,
    }


def _axis_out(axis: GraphAxis | None):
    if axis is None:
        return None
    return {
        "axis": axis.axis,
        "title": axis.title,
        "unit": axis.unit,
        "scale": axis.scale.value if isinstance(axis.scale, AxisScale) else str(axis.scale),
        "label_present": axis.label_present,
    }


def _storage_dir():
    from scix.core.config import get_settings

    return get_settings().storage_dir


def _worksheet_for(session: Session, graph: Graph) -> Worksheet | None:
    if not graph.series:
        return None
    series = graph.series[0]
    col_id = series.y_column_id or series.x_column_id
    if not col_id:
        return None
    column = session.get(Column, col_id)
    return session.get(Worksheet, column.worksheet_id) if column else None


def _extract(frame, x_col, y_col, limit: int) -> tuple[list, list]:
    if frame is None or y_col is None:
        return [], []
    if y_col.name not in frame.columns:
        return [], []
    y_values = _numeric_list(frame[y_col.name].head(limit))
    if x_col is not None and x_col.name in frame.columns:
        x_values = list(frame[x_col.name].head(limit))
        return [_plain(v) for v in x_values], y_values
    return list(range(len(y_values))), y_values


def _numeric_list(series) -> list[float | None]:
    import math

    out: list[float | None] = []
    for v in series:
        try:
            f = float(v)
        except (TypeError, ValueError):
            out.append(None)
            continue
        out.append(None if not math.isfinite(f) else f)
    return out


def _plain(value):
    import pandas as pd

    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value
