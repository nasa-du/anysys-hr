import json
import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.deps import CurrentUser, SessionDep, attendance_access
from app.core.errors import DomainError, ErrorResponse
from app.enums import ImportBatchStatus, ImportDataType, ImportSeverity
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.imports import (
    ImportBatchErrorsPublic,
    ImportBatchesPublic,
    ImportBatchPublic,
    ImportBatchRecordsPublic,
    ImportCommitPublic,
    ImportMappingTemplatePublic,
    ImportPreviewPublic,
)
from app.services.attendance import import_mapping, import_parsing
from app.services.attendance import imports as import_service
from app.services.attendance.errors import AttendanceErrorCode

router = APIRouter(
    prefix="/attendance/imports",
    tags=["attendance-imports"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}

INVALID_MAPPING_MESSAGE = "列映射格式不正确"

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
OptionalMonth = Annotated[MonthString | None, Query()]


@router.post(
    "/preview",
    response_model=ImportPreviewPublic,
    responses=ERROR_RESPONSES,
)
def preview_imports(
    session: SessionDep,
    current_user: CurrentUser,
    company_id: Annotated[uuid.UUID, Form()],
    data_type: Annotated[ImportDataType, Form()],
    month: Annotated[MonthString, Form()],
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
    sheet_name: Annotated[str | None, Form()] = None,
    column_mapping: Annotated[str | None, Form()] = None,
) -> Any:
    """Parse an uploaded or pasted file and return a persistent preview batch."""
    content: bytes | None = None
    file_name: str | None = None
    if file is not None:
        content = file.file.read(import_parsing.MAX_FILE_BYTES + 1)
        file_name = file.filename

    overrides = _decode_column_mapping(column_mapping)
    return import_service.preview_import(
        session,
        company_id=company_id,
        data_type=data_type,
        month=date.fromisoformat(f"{month}-01"),
        operator=current_user,
        content=content,
        text=text,
        file_name=file_name,
        sheet_name=sheet_name,
        column_mapping=overrides,
    )


@router.get("/", response_model=ImportBatchesPublic, responses=ERROR_RESPONSES)
def read_import_batches(
    session: SessionDep,
    company_id: uuid.UUID,
    data_type: ImportDataType | None = None,
    month: OptionalMonth = None,
    status: ImportBatchStatus | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List batch history for one company, newest first."""
    return import_service.list_batches(
        session,
        company_id=company_id,
        data_type=data_type,
        month=date.fromisoformat(f"{month}-01") if month else None,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/mapping-template",
    response_model=ImportMappingTemplatePublic,
    responses=ERROR_RESPONSES,
)
def read_mapping_template(
    session: SessionDep,
    company_id: uuid.UUID,
    data_type: ImportDataType,
) -> Any:
    """Return the saved mapping for one company and data type; 404 when absent."""
    return import_service.read_mapping_template(
        session, company_id=company_id, data_type=data_type
    )


@router.get(
    "/{batch_id}",
    response_model=ImportBatchPublic,
    responses=ERROR_RESPONSES,
)
def read_import_batch(session: SessionDep, batch_id: uuid.UUID) -> Any:
    """Return one batch with counts, mapping, and the first 20 samples."""
    return import_service.get_batch(session, batch_id)


@router.get(
    "/{batch_id}/errors",
    response_model=ImportBatchErrorsPublic,
    responses=ERROR_RESPONSES,
)
def read_import_batch_errors(
    session: SessionDep,
    batch_id: uuid.UUID,
    severity: ImportSeverity | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """Page the batch's row-level errors and warnings."""
    return import_service.list_batch_errors(
        session,
        batch_id,
        severity=severity,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{batch_id}/records",
    response_model=ImportBatchRecordsPublic,
    responses=ERROR_RESPONSES,
)
def read_import_batch_records(
    session: SessionDep,
    batch_id: uuid.UUID,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """Page the batch's normalized records with the data-type union."""
    return import_service.list_batch_records(session, batch_id, skip=skip, limit=limit)


@router.post(
    "/{batch_id}/commit",
    response_model=ImportCommitPublic,
    responses=ERROR_RESPONSES,
)
def commit_import(
    session: SessionDep,
    current_user: CurrentUser,
    batch_id: uuid.UUID,
) -> Any:
    """Commit a preview, superseding the previous batch for the same scope."""
    return import_service.commit_batch(session, batch_id, operator=current_user)


@router.post(
    "/{batch_id}/discard",
    response_model=ImportBatchPublic,
    responses=ERROR_RESPONSES,
)
def discard_import(session: SessionDep, batch_id: uuid.UUID) -> Any:
    """Discard a preview batch and delete its staged rows."""
    return import_service.discard_batch(session, batch_id)


@router.post(
    "/{batch_id}/revoke",
    response_model=ImportBatchPublic,
    responses=ERROR_RESPONSES,
)
def revoke_import(session: SessionDep, batch_id: uuid.UUID) -> Any:
    """Revoke the active committed batch in an editable month."""
    return import_service.revoke_batch(session, batch_id)


def _decode_column_mapping(raw: str | None) -> dict[str, str | int | None] | None:
    if not raw:
        return None
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        raise DomainError(
            AttendanceErrorCode.IMPORT_PARSE_FAILED,
            INVALID_MAPPING_MESSAGE,
            field_errors={"column_mapping": INVALID_MAPPING_MESSAGE},
        )
    return import_mapping.normalize_overrides(decoded)
