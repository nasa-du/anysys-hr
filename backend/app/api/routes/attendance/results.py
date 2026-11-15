import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.enums import DayStatus, DayType, ResultRosterState
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.results import (
    AttendanceDayDetailPublic,
    AttendanceDayResultsPublic,
    AttendanceMonthSummariesPublic,
    EmployeeResultCalendarPublic,
)
from app.services.attendance import results as result_service

router = APIRouter(
    prefix="/attendance/results",
    tags=["attendance-results"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]
DayStatusFilter = Annotated[list[DayStatus] | None, Query()]
FlagFilter = Annotated[list[str] | None, Query(max_length=50)]


@router.get(
    "/days/",
    response_model=AttendanceDayResultsPublic,
    responses=ERROR_RESPONSES,
)
def read_day_results(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    employee_id: uuid.UUID | None = None,
    dept_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    day_type: DayType | None = None,
    roster_state: ResultRosterState | None = None,
    day_status: DayStatusFilter = None,
    flag: FlagFilter = None,
    is_abnormal: bool | None = None,
    has_adjustment: bool | None = None,
    keyword: Keyword = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List day results; ``is_abnormal`` is derived, never stored."""
    return result_service.list_day_results(
        session,
        company_id=company_id,
        month=month,
        employee_id=employee_id,
        dept_id=dept_id,
        date_from=date_from,
        date_to=date_to,
        day_type=day_type,
        roster_state=roster_state,
        day_statuses=day_status,
        flags=flag,
        is_abnormal=is_abnormal,
        has_adjustment=has_adjustment,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/summary/",
    response_model=AttendanceMonthSummariesPublic,
    responses=ERROR_RESPONSES,
)
def read_month_summaries(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    employee_id: uuid.UUID | None = None,
    dept_id: uuid.UUID | None = None,
    keyword: Keyword = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List persisted employee month summaries for one company-month."""
    return result_service.list_month_summaries(
        session,
        company_id=company_id,
        month=month,
        employee_id=employee_id,
        dept_id=dept_id,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/calendar",
    response_model=EmployeeResultCalendarPublic,
    responses=ERROR_RESPONSES,
)
def read_result_calendar(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    employee_id: uuid.UUID,
) -> Any:
    """Return one employee's summary and day results; uncalculated months are empty."""
    return result_service.read_result_calendar(
        session,
        company_id=company_id,
        month=month,
        employee_id=employee_id,
    )


@router.get(
    "/days/{employee_id}/{work_date}",
    response_model=AttendanceDayDetailPublic,
    responses=ERROR_RESPONSES,
)
def read_day_detail(
    session: SessionDep,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    work_date: date,
) -> Any:
    """Compose roster, punches, OA rows, adjustment history, and the day result."""
    return result_service.read_day_detail(
        session,
        company_id=company_id,
        employee_id=employee_id,
        work_date=work_date,
    )
