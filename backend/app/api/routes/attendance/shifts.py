import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.models import Message
from app.schemas_attendance.core import (
    ShiftCreate,
    ShiftPublic,
    ShiftsPublic,
    ShiftUpdate,
)
from app.services.attendance import shifts as shift_service

router = APIRouter(
    prefix="/attendance/shifts",
    tags=["attendance-shifts"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/", response_model=ShiftsPublic, responses=ERROR_RESPONSES)
def read_shifts(
    session: SessionDep,
    company_id: uuid.UUID,
    keyword: Keyword = None,
    is_active: bool | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List the company's shifts ordered by shift code."""
    return shift_service.list_shifts(
        session,
        company_id=company_id,
        keyword=keyword,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/",
    response_model=ShiftPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_shift(session: SessionDep, shift_in: ShiftCreate) -> Any:
    """Create a shift template; the code and company cannot change afterwards."""
    return shift_service.create_shift(session, shift_in)


@router.get("/{shift_id}", response_model=ShiftPublic, responses=ERROR_RESPONSES)
def read_shift(session: SessionDep, shift_id: uuid.UUID) -> Any:
    """Get one shift by id."""
    return shift_service.get_shift(session, shift_id)


@router.patch("/{shift_id}", response_model=ShiftPublic, responses=ERROR_RESPONSES)
def update_shift(
    session: SessionDep,
    shift_id: uuid.UUID,
    shift_in: ShiftUpdate,
) -> Any:
    """Update a shift; deactivation is blocked while enabled plans use it."""
    return shift_service.update_shift(session, shift_id, shift_in)


@router.delete("/{shift_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_shift(session: SessionDep, shift_id: uuid.UUID) -> Any:
    """Hard delete a shift without plan or roster-snapshot references."""
    return shift_service.delete_shift(session, shift_id)
