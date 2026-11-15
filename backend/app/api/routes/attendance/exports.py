import uuid
from collections.abc import Iterator
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.schemas_attendance.common import MonthString
from app.services.attendance import exports as export_service

router = APIRouter(
    prefix="/attendance/months",
    tags=["attendance-exports"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

CSV_RESPONSES: dict[int | str, dict[str, Any]] = {
    **ERROR_RESPONSES,
    200: {
        "content": {"text/csv": {"schema": {"type": "string"}}},
        "description": "UTF-8 BOM prefixed CSV stream",
    },
}


def _csv_response(content: Iterator[str], filename: str) -> StreamingResponse:
    return StreamingResponse(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{month}/exports/payroll.csv",
    response_class=StreamingResponse,
    responses=CSV_RESPONSES,
)
def export_payroll_csv(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
) -> StreamingResponse:
    """Stream the fixed 14-column payroll CSV; header-only when empty."""
    content = export_service.payroll_csv(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
    )
    return _csv_response(content, f"attendance-payroll-{month}.csv")


@router.get(
    "/{month}/exports/detail.csv",
    response_class=StreamingResponse,
    responses=CSV_RESPONSES,
)
def export_detail_csv(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
) -> StreamingResponse:
    """Stream the union detail CSV; header-only when empty."""
    content = export_service.detail_csv(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
    )
    return _csv_response(content, f"attendance-detail-{month}.csv")
