import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.models import Message
from app.schemas_attendance.core import (
    HolidayCopyPreview,
    HolidayCopyRequest,
    HolidayCopyResult,
    HolidayCreate,
    HolidayPublic,
    HolidaysPublic,
    HolidayUpdate,
)
from app.services.attendance import holidays as holiday_service

router = APIRouter(
    prefix="/attendance/holidays",
    tags=["attendance-holidays"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Year = Annotated[int | None, Query(ge=1900, le=9999)]


@router.get("/", response_model=HolidaysPublic, responses=ERROR_RESPONSES)
def read_holidays(
    session: SessionDep,
    company_id: uuid.UUID,
    year: Year = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List the company's holiday calendar ordered by date."""
    return holiday_service.list_holidays(
        session,
        company_id=company_id,
        year=year,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/",
    response_model=HolidayPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_holiday(session: SessionDep, holiday_in: HolidayCreate) -> Any:
    """Create one holiday; ``(company_id, date)`` is unique."""
    return holiday_service.create_holiday(session, holiday_in)


# Static copy routes must be declared before the dynamic holiday id route.
@router.post(
    "/copy-year/preview",
    response_model=HolidayCopyPreview,
    responses=ERROR_RESPONSES,
)
def preview_copy_year(
    session: SessionDep,
    company_id: uuid.UUID,
    copy_in: HolidayCopyRequest,
) -> Any:
    """Preview creates and conflicts for copy-from-previous-year."""
    return holiday_service.preview_copy_year(session, company_id, copy_in)


@router.post(
    "/copy-year",
    response_model=HolidayCopyResult,
    responses=ERROR_RESPONSES,
)
def copy_year(
    session: SessionDep,
    company_id: uuid.UUID,
    copy_in: HolidayCopyRequest,
) -> Any:
    """Copy same month/day holidays; conflicts require ``overwrite = true``."""
    return holiday_service.copy_year(session, company_id, copy_in)


@router.patch("/{holiday_id}", response_model=HolidayPublic, responses=ERROR_RESPONSES)
def update_holiday(
    session: SessionDep,
    holiday_id: uuid.UUID,
    holiday_in: HolidayUpdate,
) -> Any:
    """Update name, day type, or note; the date is immutable."""
    return holiday_service.update_holiday(session, holiday_id, holiday_in)


@router.delete("/{holiday_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_holiday(session: SessionDep, holiday_id: uuid.UUID) -> Any:
    """Delete one holiday; calculated months become stale."""
    return holiday_service.delete_holiday(session, holiday_id)
