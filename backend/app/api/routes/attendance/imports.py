import json
import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import CurrentUser, SessionDep, attendance_access
from app.core.errors import DomainError, ErrorResponse
from app.enums import ImportDataType
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.imports import (
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
