import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.enums import AdjustmentStatus
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.results import (
    AttendanceAdjustmentCreate,
    AttendanceAdjustmentPublic,
    AttendanceAdjustmentsPublic,
)
from app.services.attendance import adjustments as adjustment_service

router = APIRouter(
    prefix="/attendance/results/adjustments",
    tags=["attendance-adjustments"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]


@router.get(
    "/",
    response_model=AttendanceAdjustmentsPublic,
    responses=ERROR_RESPONSES,
)
def read_adjustments(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString | None = None,
    employee_id: uuid.UUID | None = None,
    work_date: date | None = None,
    adjustment_status: Annotated[AdjustmentStatus | None, Query(alias="status")] = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List adjustment versions; there is no DELETE endpoint."""
    return adjustment_service.list_adjustments(
        session,
        company_id=company_id,
        month=month,
        employee_id=employee_id,
        work_date=work_date,
        status=adjustment_status,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/",
    response_model=AttendanceAdjustmentPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_adjustment(
    session: SessionDep,
    current_user: CurrentUser,
    adjustment_in: AttendanceAdjustmentCreate,
) -> Any:
    """Create a new version; undo is another POST restoring original values."""
    return adjustment_service.create_adjustment(
        session, adjustment_in, operator=current_user
    )


@router.get(
    "/{adjustment_id}",
    response_model=AttendanceAdjustmentPublic,
    responses=ERROR_RESPONSES,
)
def read_adjustment(session: SessionDep, adjustment_id: uuid.UUID) -> Any:
    """Get one adjustment version by id."""
    return adjustment_service.get_adjustment(session, adjustment_id)
