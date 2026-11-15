import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.core import (
    AttendanceMonthPublic,
    AttendanceMonthsPublic,
    CalcRunPublic,
    CalcRunsPublic,
)
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
Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]


@router.get("/", response_model=AttendanceMonthsPublic, responses=ERROR_RESPONSES)
def read_months(
    session: SessionDep,
    company_id: uuid.UUID,
    year: Year = None,
) -> Any:
    """List existing attendance months; synthetic drafts are not listed."""
    return month_service.list_months(session, company_id=company_id, year=year)


@router.get("/{month}", response_model=AttendanceMonthPublic, responses=ERROR_RESPONSES)
def read_month(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
) -> Any:
    """Return one month's state; an absent row is a synthetic draft."""
    return month_service.read_month(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
    )


@router.get(
    "/{month}/calc-runs/",
    response_model=CalcRunsPublic,
    responses=ERROR_RESPONSES,
)
def read_calc_runs(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List calculation runs for one company-month, newest first."""
    return month_service.list_calc_runs(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{month}/calculate",
    response_model=CalcRunPublic,
    responses=ERROR_RESPONSES,
)
def calculate_month(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
) -> Any:
    """Calculate one company-month explicitly; no automatic recalculation."""
    return month_service.calculate_month(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
    )
