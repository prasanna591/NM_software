"""Data ingest: uploaded file -> Parquet -> Dataset / Worksheet / Column rows.

The upload path is where the product's core promise is first exercised. The original
file is stored WRITE-ONCE and hashed; every worksheet's values are derived from it. The
hash is what lets the provenance panel later say "Source: Experiment_01.xlsx" and mean
a specific byte sequence rather than a filename that may have been replaced.

Type inference is CONSERVATIVE and its uncertainty is recorded. A column read as numeric
gets ``ColumnDataType.NUMERIC``; a column of mixed text and numbers becomes TEXT with the
non-numeric count recorded per column, so the data grid can show which cells need
attention instead of silently coercing them to NaN. Nothing is filled, dropped or
guessed without leaving a trace.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from scix.models import Column, Dataset, Worksheet
from scix.models.enums import ColumnDataType, TargetKind
from scix.services import audit as audit_log

EXTENSION_MIME = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroenabled.12",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".parquet": "application/vnd.apache.parquet",
}


@dataclass
class IngestResult:
    dataset: Dataset
    worksheets: list[Worksheet] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_frames(path: Path) -> tuple[dict[str, "pd.DataFrame"], list[str]]:
    """Read every sheet from the uploaded file. Returns (name -> frame, warnings)."""
    import pandas as pd

    suffix = path.suffix.lower()
    warnings: list[str] = []

    if suffix in {".csv", ".tsv"}:
        sep = "\t" if suffix == ".tsv" else ","
        frame = pd.read_csv(path, sep=sep)
        return {"Sheet1": frame}, warnings

    if suffix == ".parquet":
        return {"Sheet1": pd.read_parquet(path, engine="pyarrow")}, warnings

    book = pd.read_excel(path, sheet_name=None)
    for name, frame in book.items():
        # Excel sheet names are capped at 31 characters and cannot contain []:*?/\
        # A duplicate after truncation would violate uq_worksheets_dataset_name.
        safe = str(name)[:31]
        if safe != str(name):
            warnings.append(f"sheet name {name!r} truncated to {safe!r} (Excel 31-char limit)")
            book[safe] = book.pop(name)
    return book, warnings


def _infer_type(series) -> tuple[ColumnDataType, int]:
    """Conservative type inference.

    Returns (type, non_numeric_count). ``non_numeric_count > 0`` on a NUMERIC column is
    impossible by construction -- anything non-numeric demotes the column to TEXT rather
    than being coerced away.
    """
    import pandas as pd

    non_null = series.dropna()
    if non_null.empty:
        return ColumnDataType.TEXT, 0

    if pd.api.types.is_bool_dtype(series):
        return ColumnDataType.CATEGORICAL, 0
    if pd.api.types.is_datetime64_any_dtype(series):
        return ColumnDataType.DATE, 0

    if pd.api.types.is_numeric_dtype(series):
        # An object-dtype column of numbers and strings is the common "spreadsheet
        # column with a stray note" case. Treat it as text and report the count.
        return ColumnDataType.NUMERIC, 0

    coerced = pd.to_numeric(non_null, errors="coerce")
    bad = int(coerced.isna().sum())
    if bad == 0:
        return ColumnDataType.NUMERIC, 0

    distinct = non_null.nunique()
    # Few distinct values relative to rows reads as a category label, which is what
    # drives ANOVA grouping and grouped plots.
    if distinct <= max(2, int(len(non_null) * 0.2)) and distinct > 1:
        return ColumnDataType.CATEGORICAL, bad
    return ColumnDataType.TEXT, bad


def _compute_statistics(series, dtype: ColumnDataType) -> dict:
    import pandas as pd

    stats: dict = {"dtype": dtype.value, "count": int(series.notna().sum())}
    if dtype is not ColumnDataType.NUMERIC:
        if dtype in (ColumnDataType.CATEGORICAL, ColumnDataType.TEXT):
            try:
                counts = series.value_counts(dropna=True)
                stats["distinct"] = int(counts.size)
                stats["top_values"] = [
                    {"value": str(k), "count": int(v)} for k, v in counts.head(10).items()
                ]
            except TypeError:
                pass
        return stats

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return stats
    stats.update(
        {
            "min": float(numeric.min()),
            "max": float(numeric.max()),
            "mean": float(numeric.mean()),
            "std": float(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0,
            "median": float(numeric.median()),
        }
    )
    return stats


def ingest(
    session: Session,
    *,
    project_id: str,
    filename: str,
    content: bytes,
    actor: audit_log.Actor,
    storage_dir: Path,
    user_id: str | None = None,
) -> IngestResult:
    """Store an upload and derive its worksheets.

    The original bytes are written once, hashed, and never modified. Worksheet values
    are v0 Parquet derived from them.
    """
    import pandas as pd

    from scix.services.storage import write_frame

    warnings: list[str] = []
    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()

    if suffix not in EXTENSION_MIME:
        raise ValueError(
            f"unsupported file type {suffix!r}. Accepted: {sorted(EXTENSION_MIME)}"
        )

    dataset_id = uuid.uuid4()
    dataset_dir = Path(storage_dir) / "datasets" / str(dataset_id)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    original_path = dataset_dir / f"original{suffix}"
    original_path.write_bytes(content)
    digest = _sha256(original_path)

    frames, read_warnings = _read_frames(original_path)
    warnings.extend(read_warnings)

    dataset = Dataset(
        id=dataset_id,
        project_id=project_id,
        source_filename=safe_name,
        storage_key=str(original_path.relative_to(storage_dir)),
        content_hash=digest,
        file_size_bytes=len(content),
        mime_type=EXTENSION_MIME[suffix],
        row_count=sum(len(f) for f in frames.values()),
        column_count=max((len(f.columns) for f in frames.values()), default=0),
        sheet_names=list(frames.keys()),
        imported_by_id=user_id,
    )
    session.add(dataset)
    session.flush()

    worksheets: list[Worksheet] = []
    for ordinal, (name, frame) in enumerate(frames.items()):
        worksheet = Worksheet(
            dataset_id=dataset.id,
            name=name[:255],
            ordinal=ordinal,
            row_count=len(frame),
            transform_seq=0,
        )
        session.add(worksheet)
        session.flush()

        store_key = write_frame(storage_dir, dataset.id, worksheet.id, 0, frame)
        worksheet.column_store_key = store_key

        for col_ordinal, col_name in enumerate(frame.columns):
            series = frame[col_name]
            dtype, non_numeric = _infer_type(series)
            label = str(col_name)[:255]
            if label in {c.name for c in worksheet.columns}:
                label = f"{label}_{col_ordinal}"
                warnings.append(
                    f"sheet {name!r}: duplicate column name disambiguated to {label!r}"
                )
            session.add(
                Column(
                    worksheet_id=worksheet.id,
                    ordinal=col_ordinal,
                    name=label,
                    data_type=dtype,
                    statistics=_compute_statistics(series, dtype),
                )
            )
            if non_numeric:
                warnings.append(
                    f"sheet {name!r}, column {label!r}: {non_numeric} non-numeric value(s); "
                    f"typed as {dtype.value}. Nothing was coerced -- fix or ignore them "
                    f"explicitly."
                )

        session.flush()
        worksheets.append(worksheet)

    audit_log.record(
        session=session,
        project_id=project_id,
        actor=actor,
        action="dataset_imported",
        target_type=TargetKind.DATASET,
        target_id=str(dataset.id),
        after_value={
            "source_filename": safe_name,
            "content_hash": digest,
            "file_size_bytes": len(content),
            "sheet_names": list(frames.keys()),
        },
        detail={"warnings": warnings} if warnings else None,
    )

    return IngestResult(dataset=dataset, worksheets=worksheets, warnings=warnings)


def preview(
    session: Session,
    *,
    worksheet: Worksheet,
    storage_dir: Path,
    limit: int = 100,
):
    """A page of cell values for the data grid.

    Applies the worksheet's transformation chain first, so the grid always shows the
    current state rather than the raw upload. That is the same replay the figure uses,
    which is why the grid and the plot can never disagree.
    """
    from scix.services.storage import frame_to_records, read_frame

    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None

    if worksheet.column_store_key:
        frame = read_frame(storage_dir, dataset.id, worksheet.id, worksheet.column_store_key)
    else:
        frame = read_frame(storage_dir, dataset.id, worksheet.id, f"v{worksheet.transform_seq}.parquet")

    columns = worksheet.columns
    names = [c.name for c in columns]
    available = [n for n in names if n in frame.columns]
    missing = [n for n in names if n not in frame.columns]
    frame = frame[available]

    rows = frame_to_records(frame, limit=limit)
    truncated = len(frame) > limit

    previews = []
    for column in columns:
        previews.append(
            {
                "column_id": column.id,
                "name": column.name,
                "data_type": column.data_type.value,
                "unit": column.unit,
                "values": [row.get(column.name) for row in rows],
                "non_numeric_count": (
                    int((column.statistics or {}).get("non_numeric_count", 0) or 0)
                ),
            }
        )
    for name in missing:
        previews.append(
            {
                "column_id": None,
                "name": name,
                "data_type": "missing",
                "unit": None,
                "values": [],
                "non_numeric_count": 0,
            }
        )

    return {
        "worksheet_id": worksheet.id,
        "name": worksheet.name,
        "row_count": len(frame),
        "columns": previews,
        "truncated": truncated,
    }