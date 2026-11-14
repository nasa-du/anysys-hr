import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.schemas_attendance.core import AttendanceMonthsPublic
from app.services.attendance import months as month_service

router = APIRouter(
    prefix="/attendance/months",
    tags=["attendance-months"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Year = Annotated[int | None, Query(ge=1900, le=9999)]


@router.get("/", response_model=AttendanceMonthsPublic, responses=ERROR_RESPONSES)
def read_months(
    session: SessionDep,
    company_id: uuid.UUID,
    year: Year = None,
) -> Any:
    """List existing attendance months; synthetic drafts are not listed."""
    return month_service.list_months(session, company_id=company_id, year=year)
