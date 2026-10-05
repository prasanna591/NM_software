"""Data routes: upload, worksheets, columns, transformations, provenance."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from scix.api.deps import get_current_user, require_project
from scix.core.config import get_settings
from scix.db.session import get_db
from scix.models import (
    Column,
    DataTransformation,
    Dataset,
    Project,
    User,
    Worksheet,
)
from scix.models.enums import TargetKind, TransformType
from scix.schemas.api import (
    ColumnPatch,
    DatasetOut,
    Message,
    TransformationCreate,
    TransformationOut,
    ColumnOut,
    WorksheetDetail,
    WorksheetOut,
    WorksheetPreview,
)
from scix.services import audit as audit_log
from scix.services import ingest as ingest_service
from scix.services.chain import append as append_transform
from scix.services.chain import chain as read_chain
from scix.services.chain import replay, verify_chain

router = APIRouter()


def _require_worksheet(session: Session, worksheet_id: uuid.UUID, project: Project) -> Worksheet:
    worksheet = session.get(Worksheet, worksheet_id)
    if worksheet is None:
        raise HTTPException(status_code=404, detail="worksheet not found")
    dataset = session.get(Dataset, worksheet.dataset_id)
    if dataset is None or dataset.project_id != project.id:
        raise HTTPException(status_code=403, detail="worksheet belongs to another project")
    return worksheet


# --------------------------------------------------------------------------- #
# upload
# --------------------------------------------------------------------------- #
@router.post(
    "/data/upload",
    response_model=DatasetOut,
    status_code=201,
    tags=["data"],
)
async def upload_dataset(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Accept a spreadsheet and derive its worksheets.

    The original file is stored write-once and hashed. Nothing about the upload is
    inferred silently: type uncertainty and duplicate names come back in ``warnings``.
    """
    project: Project = require_project(project_id, session=session, user=user)

    content = await file.read()
    settings = get_settings()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"file is {len(content)} bytes; the limit is "
                f"{settings.max_upload_bytes}. Raise SCIX_MAX_UPLOAD_BYTES to change it."
            ),
        )

    try:
        result = ingest_service.ingest(
            session,
            project_id=str(project.id),
            filename=file.filename or "upload",
            content=content,
            actor=audit_log.Actor.human(str(user.id)),
            storage_dir=settings.storage_dir,
            user_id=str(user.id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session.commit()
    session.refresh(result.dataset)

    out = DatasetOut.model_validate(result.dataset)
    out.worksheets = [WorksheetOut.model_validate(w) for w in result.worksheets]
    out.sheet_names = list(result.worksheets and (result.dataset.sheet_names or [])) or []
    return out


@router.get("/datasets", response_model=list[DatasetOut], tags=["data"])
def list_datasets(
    project_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = require_project(project_id, session=session, user=user)
    datasets = session.execute(
        select(Dataset).where(Dataset.project_id == project.id).order_by(Dataset.created_at.desc())
    ).scalars().all()
    return [DatasetOut.model_validate(d) for d in datasets]


@router.get("/datasets/{dataset_id}", response_model=DatasetOut, tags=["data"])
def get_dataset(
    dataset_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    require_project(dataset.project_id, session=session, user=user)
    out = DatasetOut.model_validate(dataset)
    out.worksheets = [
        WorksheetOut.model_validate(w)
        for w in session.execute(
            select(Worksheet).where(Worksheet.dataset_id == dataset.id).order_by(Worksheet.ordinal)
        ).scalars().all()
    ]
    return out


@router.get("/datasets/{dataset_id}/worksheets", response_model=list[WorksheetOut], tags=["data"])
def list_worksheets(
    dataset_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="dataset not found")
    require_project(dataset.project_id, session=session, user=user)
    return [
        WorksheetOut.model_validate(w)
        for w in session.execute(
            select(Worksheet).where(Worksheet.dataset_id == dataset.id).order_by(Worksheet.ordinal)
        ).scalars().all()
    ]


def _worksheet_detail(worksheet: Worksheet) -> WorksheetDetail:
    """Build the response explicitly instead of ``model_validate(worksheet)``.

    The reason is subtle and worth a comment. ``ColumnOut`` exposes the JSON field
    ``metadata`` (S2 3.3), which is a *Pydantic alias* for the ORM attribute
    ``metadata_``. Letting Pydantic traverse the ``worksheet.columns`` relationship
    therefore asks it to read ``column.metadata`` -- which on any SQLAlchemy declarative
    class is ``Base.metadata``, the engine's ``MetaData`` object. Every column fails
    validation with "Input should be a valid dictionary ... MetaData()".

    Mapping the fields by hand also means the wire contract is written down explicitly,
    which is what the frontend codes against.
    """
    return WorksheetDetail(
        id=worksheet.id,
        dataset_id=worksheet.dataset_id,
        name=worksheet.name,
        ordinal=worksheet.ordinal,
        row_count=worksheet.row_count,
        transform_seq=worksheet.transform_seq,
        columns=[ColumnOut.model_validate(_column_out(c)) for c in worksheet.columns],
    )


@router.get("/worksheets/{worksheet_id}", response_model=WorksheetDetail, tags=["data"])
def get_worksheet(
    worksheet_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    worksheet = session.get(Worksheet, worksheet_id)
    if worksheet is None:
        raise HTTPException(status_code=404, detail="worksheet not found")
    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None
    require_project(dataset.project_id, session=session, user=user)

    return _worksheet_detail(worksheet)


@router.get("/worksheets/{worksheet_id}/preview", response_model=WorksheetPreview, tags=["data"])
def preview_worksheet(
    worksheet_id: uuid.UUID,
    limit: int = 100,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    worksheet = session.get(Worksheet, worksheet_id)
    if worksheet is None:
        raise HTTPException(status_code=404, detail="worksheet not found")
    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None
    require_project(dataset.project_id, session=session, user=user)

    settings = get_settings()
    try:
        return ingest_service.preview(
            session, worksheet=worksheet, storage_dir=settings.storage_dir, limit=min(limit, 1000)
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/columns/{column_id}", response_model=WorksheetDetail, tags=["data"])
def patch_column(
    column_id: uuid.UUID,
    payload: ColumnPatch,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update column metadata and roles.

    Only the fields present in the request are written. Roles are composable (S2 3.3), so
    clearing ``role_y`` must not silently clear ``is_replicate`` -- that is why this is a
    partial update and not a full replace.
    """
    column = session.get(Column, column_id)
    if column is None:
        raise HTTPException(status_code=404, detail="column not found")
    worksheet = session.get(Worksheet, column.worksheet_id)
    assert worksheet is not None
    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None
    project = require_project(dataset.project_id, session=session, user=user)

    data = payload.model_dump(exclude_unset=True, by_alias=False)
    before = {
        "name": column.name,
        "unit": column.unit,
        "role_x": column.role_x,
        "role_y": column.role_y,
        "is_replicate": column.is_replicate,
        "group_name": column.group_name,
    }
    for field, value in data.items():
        setattr(column, field, value)

    audit_log.record(
        session=session,
        project_id=str(project.id),
        actor=audit_log.Actor.human(str(user.id)),
        action="column_updated",
        target_type=TargetKind.COLUMN,
        target_id=str(column.id),
        before_value=before,
        after_value={k: getattr(column, k) for k in before},
    )
    session.commit()
    session.refresh(worksheet)

    return _worksheet_detail(worksheet)


def _column_out(c: Column):
    return {
        "id": c.id,
        "worksheet_id": c.worksheet_id,
        "ordinal": c.ordinal,
        "name": c.name,
        "unit": c.unit,
        "data_type": c.data_type,
        "role_x": c.role_x,
        "role_y": c.role_y,
        "is_replicate": c.is_replicate,
        "group_name": c.group_name,
        "error_column_id": c.error_column_id,
        "formula": c.formula,
        "metadata": c.metadata_,
        "statistics": c.statistics,
    }


# --------------------------------------------------------------------------- #
# transformations  (IRREVERSIBLE: ordered, replayable)
# --------------------------------------------------------------------------- #
@router.get("/worksheets/{worksheet_id}/transformations", response_model=list[TransformationOut], tags=["data"])
def list_transformations(
    worksheet_id: uuid.UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    worksheet = session.get(Worksheet, worksheet_id)
    if worksheet is None:
        raise HTTPException(status_code=404, detail="worksheet not found")
    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None
    require_project(dataset.project_id, session=session, user=user)
    return [TransformationOut.model_validate(t) for t in read_chain(session, str(worksheet.id))]


@router.post(
    "/data/transformations",
    response_model=TransformationOut,
    status_code=201,
    tags=["data"],
)
def create_transformation(
    project_id: uuid.UUID,
    worksheet_id: uuid.UUID,
    payload: TransformationCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Append one step to the chain. This is the only way data changes.

    Each call is a new seq. Steps are never edited or reordered -- that would make the
    stored Parquet artefacts disagree with the log, which is the state Trace must never
    produce.
    """
    project = require_project(project_id, session=session, user=user)
    worksheet = _require_worksheet(session, worksheet_id, project)

    try:
        row, warnings = append_transform(
            session,
            worksheet=worksheet,
            transform_type=payload.transform_type,
            params=payload.params,
            actor=audit_log.Actor.human(str(user.id)),
            storage_dir=get_settings().storage_dir,
            output_name=payload.output_name,
            user_id=str(user.id),
        )
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session.commit()
    session.refresh(row)
    return TransformationOut.model_validate(row)


@router.get("/worksheets/{worksheet_id}/replay", tags=["data"])
def replay_worksheet(
    worksheet_id: uuid.UUID,
    upto_seq: int | None = None,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Rebuild the worksheet state from the base file by re-executing the chain.

    The mechanism behind Trace Figure. Re-executes rather than reading stored artefacts,
    so a successful replay is evidence the chain alone reproduces the data.
    """
    worksheet = session.get(Worksheet, worksheet_id)
    if worksheet is None:
        raise HTTPException(status_code=404, detail="worksheet not found")
    dataset = session.get(Dataset, worksheet.dataset_id)
    assert dataset is not None
    require_project(dataset.project_id, session=session, user=user)

    settings = get_settings()
    problems = verify_chain(session, worksheet, settings.storage_dir)
    if problems:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "the transformation chain has gaps; replay would not reproduce the data",
                "problems": problems,
            },
        )

    try:
        frame, steps = replay(session, worksheet=worksheet, storage_dir=settings.storage_dir, upto_seq=upto_seq)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {
        "worksheet_id": str(worksheet.id),
        "replayed_steps": len(steps),
        "upto_seq": upto_seq,
        "row_count": len(frame),
        "columns": list(frame.columns),
        "chain": [
            {"seq": s.seq, "transform_type": s.transform_type.value, "params": s.params}
            for s in steps
        ],
    }
