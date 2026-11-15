import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.core import (
    AttendanceMonthPublic,
    AttendanceMonthSnapshotPublic,
    AttendanceMonthSnapshotsPublic,
    AttendanceMonthsPublic,
    AttendanceMonthUnlock,
    CalcRunPublic,
    CalcRunsPublic,
)
from app.services.attendance import months as month_service

router = APIRouter(
    prefix="/attendance/months",
    tags=["attendance-months"],
    dependencies=[Depends(attendance_access)],
)

calc_run_router = APIRouter(
    prefix="/attendance/calc-runs",
    tags=["attendance-months"],
    dependencies=[Depends(attendance_access)],
)

snapshot_router = APIRouter(
    prefix="/attendance/snapshots",
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


@router.post(
    "/{month}/confirm",
    response_model=AttendanceMonthPublic,
    responses=ERROR_RESPONSES,
)
def confirm_month(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
) -> Any:
    """Confirm calculated results that are not stale."""
    return month_service.confirm_month(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
    )


@router.post(
    "/{month}/unconfirm",
    response_model=AttendanceMonthPublic,
    responses=ERROR_RESPONSES,
)
def unconfirm_month(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
) -> Any:
    """Return a confirmed month to calculated; no reason required."""
    return month_service.unconfirm_month(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
    )


@router.post(
    "/{month}/lock",
    response_model=AttendanceMonthPublic,
    responses=ERROR_RESPONSES,
)
def lock_month(
    session: SessionDep,
    current_user: CurrentUser,
    company_id: uuid.UUID,
    month: MonthString,
) -> Any:
    """Lock a confirmed month and append an immutable snapshot."""
    return month_service.lock_month(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
        operator=current_user,
    )


@router.post(
    "/{month}/unlock",
    response_model=AttendanceMonthPublic,
    responses=ERROR_RESPONSES,
)
def unlock_month(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    unlock_in: AttendanceMonthUnlock,
) -> Any:
    """Unlock a locked month with a reason; snapshots are retained."""
    return month_service.unlock_month(
        session,
        company_id=company_id,
        month=date.fromisoformat(f"{month}-01"),
        reason=unlock_in.reason,
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


@router.get(
    "/{month}/snapshots/",
    response_model=AttendanceMonthSnapshotsPublic,
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
)
def read_snapshots(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List lock snapshots newest first; payloads are omitted."""
    return month_service.list_snapshots(
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


@calc_run_router.get(
    "/{calc_run_id}",
    response_model=CalcRunPublic,
    responses=ERROR_RESPONSES,
)
def read_calc_run(
    session: SessionDep,
    company_id: uuid.UUID,
    calc_run_id: uuid.UUID,
) -> Any:
    """Return one calculation run; cross-company access is a 404."""
    return month_service.read_calc_run(
        session,
        company_id=company_id,
        calc_run_id=calc_run_id,
    )


@snapshot_router.get(
    "/{snapshot_id}",
    response_model=AttendanceMonthSnapshotPublic,
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
)
def read_snapshot(
    session: SessionDep,
    company_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    include_payload: bool = False,
) -> Any:
    """Return one lock snapshot; the payload is opt-in."""
    return month_service.read_snapshot(
        session,
        company_id=company_id,
        snapshot_id=snapshot_id,
        include_payload=include_payload,
    )
