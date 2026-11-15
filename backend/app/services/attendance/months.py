"""Attendance-month overview and the explicit calculation trigger.

The rules page uses the month list to show which draft/calculated months a
change will mark stale and which confirmed/locked months stay untouched.
Calculation is always explicit: it takes the month row lock, builds frozen
kernel inputs from committed data, replaces the month's results in one
transaction, and writes a new ``calc_run`` (spec sections 7.1, 7.12, 8.7).
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import (
    AttendanceMonthStatus,
    CalcRunStatus,
    CalcRunTrigger,
    DayStatus,
    ImportBatchStatus,
    ImportDataType,
)
from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonth,
    AttendanceMonthSnapshot,
    AttendanceMonthSummary,
    AttendanceResultAdjustment,
    CalcRun,
    ImportBatch,
    User,
    get_datetime_utc,
)
from app.schemas_attendance.core import (
    AttendanceMonthPublic,
    AttendanceMonthSnapshotPublic,
    AttendanceMonthSnapshotsPublic,
    AttendanceMonthsPublic,
    CalcRunPublic,
    CalcRunsPublic,
    CalcRunSummary,
    InputBatches,
    InputBatchInfo,
    MonthCounts,
    SnapshotPayload,
)
from app.schemas_attendance.exports import PAYROLL_COLUMNS
from app.schemas_attendance.results import (
    AttendanceAdjustmentPublic,
    AttendanceDayResultPublic,
    AttendanceDayShiftResultPublic,
    AttendanceMonthSummaryPublic,
)
from app.services.attendance import adjustments, exports, results
from app.services.attendance.calc import CALC_VERSION, run_month
from app.services.attendance.displays import user_display_map, user_display_name
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.month_state import (
    ensure_month_editable,
    existing_month,
    lock_month_for_calculation,
)
from app.services.common import paginate
from app.services.companies import get_company_or_404

CALCULATION_FAILED_MESSAGE = "考勤计算失败，请查看计算记录"
CALCULATION_ERROR_CODE = AttendanceErrorCode.CALC_RUN_FAILED.value
MONTH_NOT_CALCULATED_MESSAGE = "考勤月份尚未计算，无法执行该操作"
MONTH_STALE_MESSAGE = "考勤结果已过期，请先重新计算"
MONTH_ALREADY_CONFIRMED_MESSAGE = "考勤月份已确认，不能重复确认"
MONTH_NOT_CONFIRMED_MESSAGE = "考勤月份尚未确认，无法执行该操作"
MONTH_ALREADY_LOCKED_MESSAGE = "考勤月份已锁定，请先解锁"
MONTH_NOT_LOCKED_MESSAGE = "考勤月份未锁定，无法解锁"
CALC_RUN_NOT_FOUND_MESSAGE = "计算记录不存在"
SNAPSHOT_NOT_FOUND_MESSAGE = "快照不存在"

ABNORMAL_DAY_STATUSES = (
    DayStatus.LATE,
    DayStatus.EARLY,
    DayStatus.MISSING_PUNCH,
    DayStatus.ABSENT,
    DayStatus.UNSCHEDULED_ATTENDANCE,
)
ABNORMAL_DAY_FLAGS = (
    "leave_trip_conflict",
    "leave_ot_conflict",
    "punch_during_leave",
    "out_of_window_punch",
)


def _counts(session: Session, month_id: uuid.UUID) -> MonthCounts:
    base = col(AttendanceDayResult.attendance_month_id) == month_id
    employee_count = session.exec(
        select(func.count(func.distinct(col(AttendanceDayResult.employee_id)))).where(
            base
        )
    ).one()
    day_result_count = session.exec(
        select(func.count()).select_from(AttendanceDayResult).where(base)
    ).one()
    abnormal_conditions: ColumnElement[bool] = or_(
        col(AttendanceDayResult.day_status).in_(ABNORMAL_DAY_STATUSES),
        *[
            col(AttendanceDayResult.day_flags).contains([flag])
            for flag in ABNORMAL_DAY_FLAGS
        ],
    )
    abnormal_day_count = session.exec(
        select(func.count())
        .select_from(AttendanceDayResult)
        .where(base, abnormal_conditions)
    ).one()
    month_summary_count = session.exec(
        select(func.count())
        .select_from(AttendanceMonthSummary)
        .where(col(AttendanceMonthSummary.attendance_month_id) == month_id)
    ).one()
    return MonthCounts(
        employee_count=employee_count,
        day_result_count=day_result_count,
        abnormal_day_count=abnormal_day_count,
        month_summary_count=month_summary_count,
    )


def _latest_calc_run(session: Session, month_id: uuid.UUID) -> CalcRun | None:
    return session.exec(
        select(CalcRun)
        .where(col(CalcRun.attendance_month_id) == month_id)
        .order_by(col(CalcRun.started_at).desc(), col(CalcRun.id).desc())
    ).first()


def _batch_info(batch: ImportBatch) -> InputBatchInfo:
    return InputBatchInfo(
        id=batch.id,
        committed_at=batch.committed_at,
        file_name=batch.file_name,
        source_rows=batch.source_rows,
        valid_records=batch.valid_records,
    )


def _active_batches(session: Session, month: AttendanceMonth) -> InputBatches:
    batches = session.exec(
        select(ImportBatch).where(
            col(ImportBatch.company_id) == month.company_id,
            col(ImportBatch.month) == month.month,
            col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
        )
    ).all()
    by_type = {batch.data_type: batch for batch in batches}

    def info(data_type: ImportDataType) -> InputBatchInfo | None:
        batch = by_type.get(data_type)
        return _batch_info(batch) if batch else None

    return InputBatches(
        punch=info(ImportDataType.PUNCH),
        trip=info(ImportDataType.TRIP),
        ot=info(ImportDataType.OT),
        leave=info(ImportDataType.LEAVE),
    )


def _month_public(session: Session, month: AttendanceMonth) -> AttendanceMonthPublic:
    calc_run = _latest_calc_run(session, month.id)
    return AttendanceMonthPublic(
        id=month.id,
        exists=True,
        company_id=month.company_id,
        month=month.month.strftime("%Y-%m"),
        status=month.status,
        is_stale=month.is_stale,
        calculated_at=month.calculated_at,
        confirmed_at=month.confirmed_at,
        locked_at=month.locked_at,
        unlock_reason=month.unlock_reason,
        latest_calc_run=(CalcRunPublic.model_validate(calc_run) if calc_run else None),
        active_batches=_active_batches(session, month),
        counts=_counts(session, month.id),
        created_at=month.created_at,
        updated_at=month.updated_at,
    )


def list_months(
    session: Session,
    *,
    company_id: uuid.UUID,
    year: int | None,
) -> AttendanceMonthsPublic:
    """List only existing company months ordered by month."""
    get_company_or_404(session, company_id)

    filters: list[ColumnElement[bool]] = [col(AttendanceMonth.company_id) == company_id]
    if year is not None:
        filters.extend(
            [
                col(AttendanceMonth.month) >= date(year, 1, 1),
                col(AttendanceMonth.month) <= date(year, 12, 1),
            ]
        )

    months = session.exec(
        select(AttendanceMonth)
        .where(*filters)
        .order_by(col(AttendanceMonth.month).asc())
    ).all()
    return AttendanceMonthsPublic(
        data=[_month_public(session, month) for month in months],
        count=len(months),
    )


def read_month(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
) -> AttendanceMonthPublic:
    """Return one month's state; an absent row is a synthetic draft, not a write."""
    get_company_or_404(session, company_id)
    month_start = month.replace(day=1)
    month_row = existing_month(session, company_id, month_start)
    if month_row is None:
        return AttendanceMonthPublic(
            id=None,
            exists=False,
            company_id=company_id,
            month=month_start.strftime("%Y-%m"),
            status=AttendanceMonthStatus.DRAFT,
            is_stale=True,
            active_batches=InputBatches(),
            counts=MonthCounts(),
        )
    return _month_public(session, month_row)


def _month_for_update(
    session: Session, company_id: uuid.UUID, month: date
) -> AttendanceMonth | None:
    return existing_month(session, company_id, month.replace(day=1), for_update=True)


def _save_month(session: Session, month_row: AttendanceMonth) -> AttendanceMonthPublic:
    session.commit()
    session.refresh(month_row)
    return _month_public(session, month_row)


def confirm_month(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
) -> AttendanceMonthPublic:
    """Confirm calculated, non-stale results (spec section 5.6)."""
    get_company_or_404(session, company_id)
    month_row = _month_for_update(session, company_id, month)
    if month_row is None or month_row.status == AttendanceMonthStatus.DRAFT:
        raise DomainError(
            AttendanceErrorCode.MONTH_NOT_CALCULATED, MONTH_NOT_CALCULATED_MESSAGE
        )
    if month_row.status == AttendanceMonthStatus.LOCKED:
        raise DomainError(
            AttendanceErrorCode.MONTH_LOCKED, MONTH_ALREADY_LOCKED_MESSAGE
        )
    if month_row.status == AttendanceMonthStatus.CONFIRMED:
        raise DomainError(
            AttendanceErrorCode.INVALID_MONTH_TRANSITION,
            MONTH_ALREADY_CONFIRMED_MESSAGE,
        )
    if month_row.is_stale:
        raise DomainError(AttendanceErrorCode.MONTH_STALE, MONTH_STALE_MESSAGE)

    now = get_datetime_utc()
    month_row.status = AttendanceMonthStatus.CONFIRMED
    month_row.confirmed_at = now
    month_row.updated_at = now
    return _save_month(session, month_row)


def unconfirm_month(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
) -> AttendanceMonthPublic:
    """Return a confirmed month to calculated; no reason required."""
    get_company_or_404(session, company_id)
    month_row = _month_for_update(session, company_id, month)
    if month_row is None:
        raise DomainError(
            AttendanceErrorCode.INVALID_MONTH_TRANSITION, MONTH_NOT_CONFIRMED_MESSAGE
        )
    if month_row.status == AttendanceMonthStatus.LOCKED:
        raise DomainError(
            AttendanceErrorCode.MONTH_LOCKED, MONTH_ALREADY_LOCKED_MESSAGE
        )
    if month_row.status != AttendanceMonthStatus.CONFIRMED:
        raise DomainError(
            AttendanceErrorCode.INVALID_MONTH_TRANSITION, MONTH_NOT_CONFIRMED_MESSAGE
        )

    now = get_datetime_utc()
    month_row.status = AttendanceMonthStatus.CALCULATED
    month_row.confirmed_at = None
    month_row.updated_at = now
    return _save_month(session, month_row)


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _snapshot_payload(
    session: Session,
    *,
    month_row: AttendanceMonth,
    calc_run: CalcRun,
    locked_at: datetime,
    locked_by: User,
) -> dict[str, Any]:
    """Freeze the locked result set into the snapshot payload (section 7.12)."""
    day_rows = session.exec(
        select(AttendanceDayResult)
        .where(col(AttendanceDayResult.attendance_month_id) == month_row.id)
        .order_by(
            col(AttendanceDayResult.work_date).asc(),
            col(AttendanceDayResult.employee_id).asc(),
        )
    ).all()
    shift_rows = session.exec(
        select(AttendanceDayShiftResult)
        .where(col(AttendanceDayShiftResult.calc_run_id) == calc_run.id)
        .order_by(
            col(AttendanceDayShiftResult.work_date).asc(),
            col(AttendanceDayShiftResult.employee_id).asc(),
            col(AttendanceDayShiftResult.seq).asc(),
        )
    ).all()
    summary_rows = session.exec(
        select(AttendanceMonthSummary)
        .where(col(AttendanceMonthSummary.attendance_month_id) == month_row.id)
        .order_by(col(AttendanceMonthSummary.employee_id).asc())
    ).all()
    adjustment_rows = session.exec(
        select(AttendanceResultAdjustment)
        .where(col(AttendanceResultAdjustment.attendance_month_id) == month_row.id)
        .order_by(
            col(AttendanceResultAdjustment.work_date).asc(),
            col(AttendanceResultAdjustment.employee_id).asc(),
            col(AttendanceResultAdjustment.version).asc(),
        )
    ).all()
    names = user_display_map(session, {row.adjusted_by for row in adjustment_rows})

    adjustments_payload: list[dict[str, Any]] = []
    for row in adjustment_rows:
        public = AttendanceAdjustmentPublic.model_validate(row)
        public.adjusted_by_name = names.get(row.adjusted_by)
        adjustments_payload.append(public.model_dump(mode="json"))

    payload = SnapshotPayload(
        company_id=month_row.company_id,
        month=month_row.month.strftime("%Y-%m"),
        locked_at=locked_at,
        locked_by=locked_by.id,
        attendance_month={
            "status": AttendanceMonthStatus.LOCKED.value,
            "calculated_at": _isoformat(month_row.calculated_at),
            "confirmed_at": _isoformat(month_row.confirmed_at),
        },
        calc_run={
            "id": str(calc_run.id),
            "trigger": calc_run.trigger.value,
            "calc_version": calc_run.calc_version,
            "rules_version": calc_run.rules_version,
            "roster_version": calc_run.roster_version,
            "rules_snapshot": calc_run.rules_snapshot,
            "input_batches": calc_run.input_batches,
            "summary": calc_run.summary,
        },
        day_results=[
            AttendanceDayResultPublic.model_validate(row).model_dump(mode="json")
            for row in day_rows
        ],
        shift_results=[
            AttendanceDayShiftResultPublic.model_validate(row).model_dump(mode="json")
            for row in shift_rows
        ],
        month_summaries=[
            AttendanceMonthSummaryPublic.model_validate(row).model_dump(mode="json")
            for row in summary_rows
        ],
        adjustments=adjustments_payload,
        export={
            "columns": list(PAYROLL_COLUMNS),
            "rows": exports.payroll_rows(
                session,
                company_id=month_row.company_id,
                month=month_row.month,
            ),
        },
    )
    return payload.model_dump(mode="json")


def lock_month(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    operator: User,
) -> AttendanceMonthPublic:
    """Lock a confirmed month and append an immutable snapshot."""
    get_company_or_404(session, company_id)
    month_row = _month_for_update(session, company_id, month)
    if month_row is None or month_row.status == AttendanceMonthStatus.DRAFT:
        raise DomainError(
            AttendanceErrorCode.MONTH_NOT_CALCULATED, MONTH_NOT_CALCULATED_MESSAGE
        )
    if month_row.status == AttendanceMonthStatus.LOCKED:
        raise DomainError(
            AttendanceErrorCode.MONTH_LOCKED, MONTH_ALREADY_LOCKED_MESSAGE
        )
    if month_row.status != AttendanceMonthStatus.CONFIRMED:
        raise DomainError(
            AttendanceErrorCode.INVALID_MONTH_TRANSITION, MONTH_NOT_CONFIRMED_MESSAGE
        )

    calc_run = session.exec(
        select(CalcRun)
        .where(
            col(CalcRun.attendance_month_id) == month_row.id,
            col(CalcRun.status) == CalcRunStatus.SUCCESS,
        )
        .order_by(col(CalcRun.started_at).desc(), col(CalcRun.id).desc())
    ).first()
    if calc_run is None:
        raise DomainError(
            AttendanceErrorCode.MONTH_NOT_CALCULATED, MONTH_NOT_CALCULATED_MESSAGE
        )

    current_version = session.exec(
        select(func.max(AttendanceMonthSnapshot.version)).where(
            col(AttendanceMonthSnapshot.attendance_month_id) == month_row.id
        )
    ).one()
    now = get_datetime_utc()
    payload = _snapshot_payload(
        session,
        month_row=month_row,
        calc_run=calc_run,
        locked_at=now,
        locked_by=operator,
    )
    snapshot = AttendanceMonthSnapshot(
        attendance_month_id=month_row.id,
        calc_run_id=calc_run.id,
        version=(current_version or 0) + 1,
        locked_at=now,
        locked_by=operator.id,
        payload=payload,
    )
    session.add(snapshot)

    month_row.status = AttendanceMonthStatus.LOCKED
    month_row.locked_at = now
    month_row.updated_at = now
    return _save_month(session, month_row)


def unlock_month(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    reason: str,
) -> AttendanceMonthPublic:
    """Unlock a locked month, keep snapshots, and require recalculation."""
    get_company_or_404(session, company_id)
    month_row = _month_for_update(session, company_id, month)
    if month_row is None or month_row.status != AttendanceMonthStatus.LOCKED:
        raise DomainError(
            AttendanceErrorCode.INVALID_MONTH_TRANSITION, MONTH_NOT_LOCKED_MESSAGE
        )

    now = get_datetime_utc()
    month_row.status = AttendanceMonthStatus.CALCULATED
    month_row.is_stale = True
    month_row.locked_at = None
    month_row.confirmed_at = None
    month_row.unlock_reason = reason
    month_row.updated_at = now
    return _save_month(session, month_row)


def list_calc_runs(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    skip: int,
    limit: int,
) -> CalcRunsPublic:
    """List calculation runs newest first; an uncalculated month has no runs."""
    get_company_or_404(session, company_id)
    month_row = existing_month(session, company_id, month.replace(day=1))
    if month_row is None:
        return CalcRunsPublic(data=[], count=0)
    filters = [col(CalcRun.attendance_month_id) == month_row.id]
    statement = (
        select(CalcRun)
        .where(*filters)
        .order_by(col(CalcRun.started_at).desc(), col(CalcRun.id).desc())
    )
    count_statement = select(func.count()).select_from(CalcRun).where(*filters)
    runs, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return CalcRunsPublic(
        data=[CalcRunPublic.model_validate(run) for run in runs], count=count
    )


def read_calc_run(
    session: Session,
    *,
    company_id: uuid.UUID,
    calc_run_id: uuid.UUID,
) -> CalcRunPublic:
    """Return one calculation run; cross-company access is a 404."""
    get_company_or_404(session, company_id)
    calc_run = session.get(CalcRun, calc_run_id)
    if calc_run is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, CALC_RUN_NOT_FOUND_MESSAGE)
    month_row = session.get(AttendanceMonth, calc_run.attendance_month_id)
    if month_row is None or month_row.company_id != company_id:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, CALC_RUN_NOT_FOUND_MESSAGE)
    return CalcRunPublic.model_validate(calc_run)


def _snapshot_public(
    snapshot: AttendanceMonthSnapshot,
    *,
    calc_run: CalcRun | None,
    locked_by_name: str | None,
    include_payload: bool,
) -> AttendanceMonthSnapshotPublic:
    public = AttendanceMonthSnapshotPublic.model_validate(snapshot)
    public.locked_by_name = locked_by_name
    if calc_run is not None and calc_run.summary is not None:
        public.summary = CalcRunSummary.model_validate(calc_run.summary)
    if include_payload:
        public.payload = SnapshotPayload.model_validate(snapshot.payload)
    else:
        public.payload = None
    return public


def _snapshot_context(
    session: Session, snapshots: list[AttendanceMonthSnapshot]
) -> tuple[dict[uuid.UUID, CalcRun], dict[uuid.UUID, str | None]]:
    calc_run_ids = {snapshot.calc_run_id for snapshot in snapshots}
    runs = (
        {
            run.id: run
            for run in session.exec(
                select(CalcRun).where(col(CalcRun.id).in_(calc_run_ids))
            ).all()
        }
        if calc_run_ids
        else {}
    )
    names = user_display_map(session, {snapshot.locked_by for snapshot in snapshots})
    return runs, names


def list_snapshots(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    skip: int,
    limit: int,
) -> AttendanceMonthSnapshotsPublic:
    """List lock snapshots newest version first; payloads are omitted."""
    get_company_or_404(session, company_id)
    month_row = existing_month(session, company_id, month.replace(day=1))
    if month_row is None:
        return AttendanceMonthSnapshotsPublic(data=[], count=0)

    filters = [col(AttendanceMonthSnapshot.attendance_month_id) == month_row.id]
    statement = (
        select(AttendanceMonthSnapshot)
        .where(*filters)
        .order_by(
            col(AttendanceMonthSnapshot.version).desc(),
            col(AttendanceMonthSnapshot.id).desc(),
        )
    )
    count_statement = (
        select(func.count()).select_from(AttendanceMonthSnapshot).where(*filters)
    )
    snapshots, count = paginate(
        session, statement, count_statement, skip=skip, limit=limit
    )
    runs, names = _snapshot_context(session, snapshots)
    return AttendanceMonthSnapshotsPublic(
        data=[
            _snapshot_public(
                snapshot,
                calc_run=runs.get(snapshot.calc_run_id),
                locked_by_name=names.get(snapshot.locked_by),
                include_payload=False,
            )
            for snapshot in snapshots
        ],
        count=count,
    )


def read_snapshot(
    session: Session,
    *,
    company_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    include_payload: bool,
) -> AttendanceMonthSnapshotPublic:
    """Return one snapshot; payload only when requested."""
    get_company_or_404(session, company_id)
    snapshot = session.get(AttendanceMonthSnapshot, snapshot_id)
    if snapshot is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, SNAPSHOT_NOT_FOUND_MESSAGE)
    month_row = session.get(AttendanceMonth, snapshot.attendance_month_id)
    if month_row is None or month_row.company_id != company_id:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, SNAPSHOT_NOT_FOUND_MESSAGE)
    calc_run = session.get(CalcRun, snapshot.calc_run_id)
    operator = session.get(User, snapshot.locked_by)
    return _snapshot_public(
        snapshot,
        calc_run=calc_run,
        locked_by_name=user_display_name(operator),
        include_payload=include_payload,
    )


def _resolve_trigger(
    session: Session,
    month_id: uuid.UUID,
    requested: CalcRunTrigger | None,
) -> CalcRunTrigger:
    """First successful calculation is ``initial``; later ones are ``manual``."""
    if requested is not None:
        return requested
    previous_success = session.exec(
        select(CalcRun.id).where(
            col(CalcRun.attendance_month_id) == month_id,
            col(CalcRun.status) == CalcRunStatus.SUCCESS,
        )
    ).first()
    return (
        CalcRunTrigger.MANUAL
        if previous_success is not None
        else CalcRunTrigger.INITIAL
    )


def _record_failed_calc_run(
    session: Session,
    *,
    company_id: uuid.UUID,
    month_start: date,
    month_id: uuid.UUID,
    trigger: CalcRunTrigger,
    started_at: datetime,
    error: Exception,
    calculation_data: results.MonthCalculationData | None,
) -> CalcRun:
    """Write a failed run in its own transaction after the rollback.

    ``calc_run.rules_snapshot`` and ``input_batches`` are NOT NULL, so a run
    that failed before the adapter finished records the documented system
    defaults rather than leaving the audit row unreadable.
    """
    if calculation_data is not None:
        rules_snapshot = calculation_data.rules_snapshot
        input_batches = calculation_data.input_batches
        rules_version = calculation_data.rules_version
        roster_version = calculation_data.roster_version
    else:
        rules_snapshot = results.default_rules_snapshot()
        input_batches = results.empty_input_batches()
        rules_version = results.canonical_hash(rules_snapshot)
        roster_version = results.roster_fingerprint((), ())

    month_row = session.get(AttendanceMonth, month_id)
    if month_row is None:
        # The first calculation created the month inside the rolled-back
        # result transaction; recreate it so the failed run has its parent.
        month_row = AttendanceMonth(
            id=month_id,
            company_id=company_id,
            month=month_start,
            status=AttendanceMonthStatus.DRAFT,
            is_stale=True,
        )
        try:
            session.add(month_row)
            session.flush()
        except IntegrityError:
            session.rollback()
            month_row = existing_month(session, company_id, month_start)
            if month_row is None:
                raise

    failed_run = CalcRun(
        attendance_month_id=month_row.id,
        trigger=trigger,
        status=CalcRunStatus.FAILED,
        calc_version=CALC_VERSION,
        rules_version=rules_version,
        roster_version=roster_version,
        rules_snapshot=rules_snapshot,
        input_batches=input_batches,
        summary=None,
        error_code=CALCULATION_ERROR_CODE,
        error_message=f"{type(error).__name__}: {error}"[:500],
        started_at=started_at,
        finished_at=get_datetime_utc(),
    )
    session.add(failed_run)
    session.commit()
    session.refresh(failed_run)
    return failed_run


def calculate_month(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    trigger: CalcRunTrigger | None = None,
) -> CalcRun:
    """Calculate one company-month and persist its results explicitly.

    The month row is locked for the whole transaction. A concurrent
    calculation fails with ``calc_in_progress`` instead of queueing. Any
    failure rolls back the result transaction, keeps old results untouched,
    and writes a separate failed ``calc_run`` (spec section 7.12).
    """
    get_company_or_404(session, company_id)
    month_start = month.replace(day=1)
    month_row = lock_month_for_calculation(session, company_id, month_start)
    ensure_month_editable(month_row)

    started_at = get_datetime_utc()
    month_id = month_row.id
    resolved_trigger = _resolve_trigger(session, month_id, trigger)
    calculation_data: results.MonthCalculationData | None = None
    try:
        calculation_data = results.build_month_inputs(
            session, company_id=company_id, month=month_start
        )
        outputs = run_month(calculation_data.inputs)

        finished_at = get_datetime_utc()
        calc_run = CalcRun(
            attendance_month_id=month_row.id,
            trigger=resolved_trigger,
            status=CalcRunStatus.SUCCESS,
            calc_version=CALC_VERSION,
            rules_version=calculation_data.rules_version,
            roster_version=calculation_data.roster_version,
            rules_snapshot=calculation_data.rules_snapshot,
            input_batches=calculation_data.input_batches,
            summary=results.summary_payload(outputs.summary),
            started_at=started_at,
            finished_at=finished_at,
        )
        session.add(calc_run)
        session.flush()
        results.replace_month_results(
            session,
            month=month_row,
            calc_run_id=calc_run.id,
            data=calculation_data,
            outputs=outputs,
        )
        adjustments.reapply_active_adjustments(session, month_id=month_row.id)

        month_row.status = AttendanceMonthStatus.CALCULATED
        month_row.is_stale = False
        month_row.calculated_at = finished_at
        month_row.updated_at = finished_at
        session.commit()
    except Exception as error:
        session.rollback()
        failed_run = _record_failed_calc_run(
            session,
            company_id=company_id,
            month_start=month_start,
            month_id=month_id,
            trigger=resolved_trigger,
            started_at=started_at,
            error=error,
            calculation_data=calculation_data,
        )
        raise DomainError(
            AttendanceErrorCode.CALC_RUN_FAILED,
            CALCULATION_FAILED_MESSAGE,
            calc_run_id=failed_run.id,
        ) from error

    session.refresh(calc_run)
    return calc_run
