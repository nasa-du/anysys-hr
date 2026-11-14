import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.enums import RosterSource, RosterState
from app.models import Message
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.scheduling import (
    EmployeeRosterCalendarPublic,
    PersonnelSyncPreview,
    PersonnelSyncRequest,
    PersonnelSyncResult,
    RosterDayPublic,
    RosterEmployeeSummariesPublic,
    RosterEntriesPublic,
    RosterEntryBatchRequest,
    RosterEntryBatchResult,
    RosterEntryCreate,
    RosterEntryPublic,
    RosterEntryUpdate,
    RosterMonthPublic,
)
from app.services.attendance import roster as roster_service

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]

roster_router = APIRouter(
    prefix="/attendance/roster",
    tags=["attendance-roster"],
    dependencies=[Depends(attendance_access)],
)

entries_router = APIRouter(
    prefix="/attendance/roster-entries",
    tags=["attendance-roster"],
    dependencies=[Depends(attendance_access)],
)


@roster_router.get(
    "/calendar",
    response_model=EmployeeRosterCalendarPublic,
    responses=ERROR_RESPONSES,
)
def read_employee_calendar(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    employee_id: uuid.UUID,
) -> Any:
    """Return one employee's full month; dates without a row are unscheduled."""
    return roster_service.read_employee_calendar(
        session, company_id=company_id, month=month, employee_id=employee_id
    )


@roster_router.get("/day", response_model=RosterDayPublic, responses=ERROR_RESPONSES)
def read_roster_day(
    session: SessionDep,
    company_id: uuid.UUID,
    work_date: Annotated[date, Query(alias="date")],
    dept_id: uuid.UUID | None = None,
    plan_id: uuid.UUID | None = None,
    source: RosterSource | None = None,
) -> Any:
    """Return who works that day plus the count of employed but unscheduled staff."""
    return roster_service.read_roster_day(
        session,
        company_id=company_id,
        work_date=work_date,
        dept_id=dept_id,
        plan_id=plan_id,
        source=source,
    )


@roster_router.get(
    "/month", response_model=RosterMonthPublic, responses=ERROR_RESPONSES
)
def read_roster_month(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    dept_id: uuid.UUID | None = None,
) -> Any:
    """Return daily counts, shift counts, and the month's plans."""
    return roster_service.read_roster_month(
        session, company_id=company_id, month=month, dept_id=dept_id
    )


@roster_router.get(
    "/employees",
    response_model=RosterEmployeeSummariesPublic,
    responses=ERROR_RESPONSES,
)
def read_roster_employees(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    dept_id: uuid.UUID | None = None,
    keyword: Keyword = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """Return per-employee work/rest/unscheduled counts for the month."""
    return roster_service.read_roster_employees(
        session,
        company_id=company_id,
        month=month,
        dept_id=dept_id,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )


@roster_router.get(
    "/sync-preview",
    response_model=PersonnelSyncPreview,
    responses=ERROR_RESPONSES,
)
def sync_preview(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
) -> Any:
    """Dry-run personnel sync without writing roster rows."""
    return roster_service.sync_preview(session, company_id=company_id, month=month)


@roster_router.post(
    "/sync", response_model=PersonnelSyncResult, responses=ERROR_RESPONSES
)
def sync_personnel(session: SessionDep, sync_in: PersonnelSyncRequest) -> Any:
    """Apply a full company-month re-expansion in one transaction."""
    return roster_service.sync_personnel(session, sync_in)


@entries_router.get("/", response_model=RosterEntriesPublic, responses=ERROR_RESPONSES)
def read_roster_entries(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString | None = None,
    employee_id: uuid.UUID | None = None,
    dept_id: uuid.UUID | None = None,
    state: RosterState | None = None,
    source: RosterSource | None = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List persisted roster rows only; unscheduled dates have no row."""
    return roster_service.list_roster_entries(
        session,
        company_id=company_id,
        month=month,
        employee_id=employee_id,
        dept_id=dept_id,
        state=state,
        source=source,
        skip=skip,
        limit=limit,
    )


@entries_router.get(
    "/{entry_id}", response_model=RosterEntryPublic, responses=ERROR_RESPONSES
)
def read_roster_entry(session: SessionDep, entry_id: uuid.UUID) -> Any:
    """Get one roster entry with its shift snapshots."""
    return roster_service.get_roster_entry(session, entry_id)


@entries_router.post(
    "/",
    response_model=RosterEntryPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_roster_entry(session: SessionDep, entry_in: RosterEntryCreate) -> Any:
    """Create a manual exception, overriding a plan row when one exists."""
    return roster_service.create_roster_entry(session, entry_in)


@entries_router.patch(
    "/{entry_id}", response_model=RosterEntryPublic, responses=ERROR_RESPONSES
)
def update_roster_entry(
    session: SessionDep,
    entry_id: uuid.UUID,
    entry_in: RosterEntryUpdate,
) -> Any:
    """Edit a manual exception; plan-generated rows return 409."""
    return roster_service.update_roster_entry(session, entry_id, entry_in)


@entries_router.delete("/{entry_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_roster_entry(session: SessionDep, entry_id: uuid.UUID) -> Any:
    """Delete a manual exception and restore the current plan resolution."""
    return roster_service.delete_roster_entry(session, entry_id)


@entries_router.post(
    "/batch",
    response_model=RosterEntryBatchResult,
    responses=ERROR_RESPONSES,
)
def batch_roster_entries(session: SessionDep, batch_in: RosterEntryBatchRequest) -> Any:
    """Apply a batch of manual exceptions all-or-nothing."""
    return roster_service.batch_entries(session, batch_in)
