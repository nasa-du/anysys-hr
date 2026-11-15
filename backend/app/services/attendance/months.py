"""Attendance-month overview and the explicit calculation trigger.

The rules page uses the month list to show which draft/calculated months a
change will mark stale and which confirmed/locked months stay untouched.
Calculation is always explicit: it takes the month row lock, builds frozen
kernel inputs from committed data, replaces the month's results in one
transaction, and writes a new ``calc_run`` (spec sections 7.1, 7.12, 8.7).
"""

import uuid
from datetime import date, datetime

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
    AttendanceMonth,
    AttendanceMonthSummary,
    CalcRun,
    ImportBatch,
    get_datetime_utc,
)
from app.schemas_attendance.core import (
    AttendanceMonthPublic,
    AttendanceMonthsPublic,
    CalcRunPublic,
    CalcRunsPublic,
    InputBatches,
    InputBatchInfo,
    MonthCounts,
)
from app.services.attendance import adjustments, results
from app.services.attendance.calc import CALC_VERSION, run_month
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
