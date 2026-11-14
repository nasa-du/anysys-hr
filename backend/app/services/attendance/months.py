"""Read-only attendance-month overview.

The rules page uses the month list to show which draft/calculated months a
change will mark stale and which confirmed/locked months stay untouched.
Month state transitions, snapshots, and calculation land with later slices.
"""

import uuid
from datetime import date

from sqlalchemy import ColumnElement, func, or_
from sqlmodel import Session, col, select

from app.enums import (
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
)
from app.schemas_attendance.core import (
    AttendanceMonthPublic,
    AttendanceMonthsPublic,
    CalcRunPublic,
    InputBatches,
    InputBatchInfo,
    MonthCounts,
)
from app.services.companies import get_company_or_404

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
