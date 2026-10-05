"""Appending to and replaying the transformation chain.

Kept separate from :mod:`scix.services.transforms` because that module is deliberately
pure -- no session, no filesystem. This one owns both, and is the only place allowed to
decide what a new ``seq`` is.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from scix.models import Column, DataTransformation, Dataset, Worksheet
from scix.models.enums import TargetKind, TransformType
from scix.services import audit as audit_log
from scix.services.storage import read_frame, write_frame
from scix.services.transforms import TransformError, apply_transform


def append(
    session: Session,
    *,
    worksheet: Worksheet,
    transform_type: TransformType,
    params: dict,
    actor: audit_log.Actor,
    storage_dir: Path,
    output_name: str | None = None,
    user_id: str | None = None,
) -> tuple[DataTransformation, list[str]]:
    """Apply one step and append it to the log. Returns (row, warnings).

    Ordering is transactional: the new seq, the Parquet write and the worksheet's
    ``transform_seq`` advance happen together. If the write fails, the row is never
    committed, so seq can never advance past a step whose artefact is missing.
    """
    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None

    base_key = worksheet.column_store_key or f"v{worksheet.transform_seq}.parquet"
    frame = read_frame(storage_dir, dataset.id, worksheet.id, base_key)

    rows_before = len(frame)
    new_frame, inputs, outputs = apply_transform(frame, transform_type, params, output_name)

    next_seq = worksheet.transform_seq + 1
    store_key = write_frame(storage_dir, dataset.id, worksheet.id, next_seq, new_frame)

    row = DataTransformation(
        worksheet_id=worksheet.id,
        seq=next_seq,
        transform_type=transform_type,
        params={**params, **({"output_name": output_name} if output_name else {})},
        input_columns=inputs,
        output_columns=outputs,
        rows_before=rows_before,
        rows_after=len(new_frame),
        output_store_key=store_key,
        applied_by_id=user_id,
        applied_at=datetime.now(timezone.utc),
    )
    session.add(row)

    worksheet.transform_seq = next_seq
    worksheet.column_store_key = store_key
    worksheet.row_count = len(new_frame)
    session.flush()

    _sync_column_metadata(session, worksheet, new_frame, outputs)

    audit_log.record(
        session=session,
        project_id=worksheet.dataset.project_id,
        actor=actor,
        action="transform_applied",
        target_type=TargetKind.DATA_TRANSFORMATION,
        target_id=str(row.id),
        after_value={
            "seq": next_seq,
            "transform_type": transform_type.value,
            "rows_before": rows_before,
            "rows_after": len(new_frame),
        },
        detail={"params": params, "warnings": None},
    )

    warnings = list((row.params or {}).get("_warnings", []))
    return row, warnings


def _sync_column_metadata(session: Session, worksheet: Worksheet, frame, outputs: list[str]) -> None:
    """Refresh the column list for anything the chain produced or removed.

    A calculated column is new and must appear in the grid. A filtered worksheet may have
    lost rows but not columns. A merge may have added columns. Without this the metadata
    layer drifts from the Parquet layer, and the data grid silently omits data.
    """
    from scix.models.enums import ColumnDataType

    existing = {c.name: c for c in worksheet.columns}

    for name in outputs:
        if name in frame.columns and name not in existing:
            session.add(
                Column(
                    worksheet_id=worksheet.id,
                    ordinal=len(existing),
                    name=name[:255],
                    data_type=ColumnDataType.NUMERIC,
                    statistics={"derived": True},
                )
            )
            existing[name] = None  # type: ignore[assignment]

    for name, column in existing.items():
        if column is None or name not in frame.columns:
            continue
        series = frame[name]
        try:
            import pandas as pd

            if pd.api.types.is_numeric_dtype(series) and column.data_type is ColumnDataType.NUMERIC:
                numeric = pd.to_numeric(series, errors="coerce").dropna()
                column.statistics = {
                    **(column.statistics or {}),
                    "count": int(numeric.size),
                    "min": float(numeric.min()) if numeric.size else None,
                    "max": float(numeric.max()) if numeric.size else None,
                    "mean": float(numeric.mean()) if numeric.size else None,
                }
        except (TypeError, ValueError):
            pass


def replay(
    session: Session,
    *,
    worksheet: Worksheet,
    storage_dir: Path,
    upto_seq: int | None = None,
) -> tuple[object, list[DataTransformation]]:
    """Rebuild a worksheet state from the base file by re-executing the chain.

    Returns (frame, steps). This is the mechanism behind Trace Figure: it can produce
    the state at any ``seq``, which is what "returns to the underlying dataset" means in
    practice.

    It re-executes rather than reading the stored Parquet artefacts. That is a
    deliberate choice: reading the artefacts would be faster but would prove nothing,
    whereas re-execution demonstrates that the chain alone reproduces the data -- which is
    the reproducibility claim being made.
    """
    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None

    frame = _read_base(dataset, worksheet, storage_dir)

    steps = (
        session.query(DataTransformation)
        .filter(DataTransformation.worksheet_id == worksheet.id)
        .order_by(DataTransformation.seq)
        .all()
    )

    if upto_seq is not None:
        steps = [s for s in steps if s.seq <= upto_seq]

    applied: list[DataTransformation] = []
    for step in steps:
        params = dict(step.params or {})
        params.pop("_warnings", None)
        output_name = params.pop("output_name", None)
        frame, _, _ = apply_transform(frame, step.transform_type, params, output_name)
        applied.append(step)

    return frame, applied


def _read_base(dataset: Dataset, worksheet: Worksheet, storage_dir: Path):
    """The untransformed values for THIS worksheet, at seq 0.

    Must select the right sheet. Reading the first sheet of the workbook would replay a
    two-worksheet dataset against the wrong data -- and every derived statistic, figure
    and provenance record would then be confidently wrong about its source.
    """
    from scix.services.ingest import _read_frames

    original = storage_dir / dataset.storage_key
    frames, _ = _read_frames(original)

    name = worksheet.name
    if name in frames:
        return frames[name]

    # The worksheet name was truncated to 255 chars on insert but the frame keeps the
    # original header. Match by position as the fallback.
    if 0 <= worksheet.ordinal < len(frames):
        ordered = list(frames.values())
        return ordered[worksheet.ordinal]

    raise TransformError(
        f"worksheet {name!r} (ordinal {worksheet.ordinal}) is not present in "
        f"{dataset.source_filename}. Sheets in the file: {list(frames)}. Re-import the "
        f"file rather than replaying against a sheet that is not there."
    )


def chain(session: Session, worksheet_id: str) -> list[DataTransformation]:
    return (
        session.query(DataTransformation)
        .filter(DataTransformation.worksheet_id == worksheet_id)
        .order_by(DataTransformation.seq)
        .all()
    )


def verify_chain(session: Session, worksheet: Worksheet, storage_dir: Path) -> list[str]:
    """Report gaps between the log and the Parquet artefacts.

    A gap means Trace cannot reach that state. Surfaced as warnings rather than raised so
    the UI can warn the researcher while still letting them work.
    """
    problems: list[str] = []
    steps = chain(session, worksheet.id)

    expected = 1
    for step in steps:
        if step.seq != expected:
            problems.append(
                f"chain gap: expected seq {expected}, found {step.seq}. Provenance cannot "
                f"reconstruct the missing step."
            )
        expected = step.seq + 1

    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None
    for step in steps:
        if not step.output_store_key:
            problems.append(f"seq {step.seq}: no stored artefact recorded")
            continue
        if not (storage_dir / step.output_store_key).exists():
            problems.append(f"seq {step.seq}: artefact {step.output_store_key} is missing from disk")

    return problems