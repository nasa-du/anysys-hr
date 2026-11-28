"""Read-only attendance contract consumed by payroll.

Payroll reads locked attendance months only, in-process, through this module.
It returns the nine payroll-relevant month-summary values plus the locked
source metadata as frozen dataclasses and never writes attendance or payroll
tables. Attendance imports no payroll code.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import AttendanceMonthStatus
from app.models import (
    AttendanceMonth,
    AttendanceMonthSnapshot,
    AttendanceMonthSummary,
    CalcRun,
)

DAY_QUANTUM = Decimal("0.1")
AMOUNT_QUANTUM = Decimal("0.01")

MONTH_MISSING_MESSAGE = "考勤月份不存在"
MONTH_NOT_LOCKED_MESSAGE = "考勤月份未锁定"
SUMMARY_MISSING_MESSAGE = "员工缺少考勤月汇总"
SOURCE_INCONSISTENT_MESSAGE = "考勤月汇总与锁定快照的计算批次不一致"

__all__ = [
    "AttendanceReadErrorCode",
    "AttendanceSource",
    "AttendanceSourceValues",
    "read_locked_month_summary",
]


class AttendanceReadErrorCode(StrEnum):
    MONTH_MISSING = "attendance_month_missing"
    MONTH_NOT_LOCKED = "attendance_month_not_locked"
    SUMMARY_MISSING = "attendance_summary_missing"
    SOURCE_INCONSISTENT = "attendance_source_inconsistent"


@dataclass(frozen=True)
class AttendanceSourceValues:
    """The nine attendance-owned values payroll consumes."""

    weekday_full: Decimal
    weekend_full: Decimal
    weekday_attended: Decimal
    weekend_attended: Decimal
    paid_leave_days: Decimal
    ot_weekday_hours: Decimal
    ot_weekend_hours: Decimal
    ot_holiday_hours: Decimal
    attendance_deduct: Decimal


@dataclass(frozen=True)
class AttendanceSource:
    """One employee's month summary plus the locked source identifiers."""

    attendance_month_id: uuid.UUID
    attendance_snapshot_id: uuid.UUID
    attendance_snapshot_version: int
    attendance_calc_run_id: uuid.UUID
    calc_version: str
    rules_version: str
    locked_at: datetime
    values: AttendanceSourceValues


def _quantized(value: Decimal, quantum: Decimal) -> Decimal:
    return Decimal(value).quantize(quantum)


def _source_inconsistent() -> DomainError:
    return DomainError(
        AttendanceReadErrorCode.SOURCE_INCONSISTENT, SOURCE_INCONSISTENT_MESSAGE
    )


def _summary_values(summary: AttendanceMonthSummary) -> AttendanceSourceValues:
    return AttendanceSourceValues(
        weekday_full=_quantized(summary.weekday_full, DAY_QUANTUM),
        weekend_full=_quantized(summary.weekend_full, DAY_QUANTUM),
        weekday_attended=_quantized(summary.weekday_attended, DAY_QUANTUM),
        weekend_attended=_quantized(summary.weekend_attended, DAY_QUANTUM),
        paid_leave_days=_quantized(summary.paid_leave_days, DAY_QUANTUM),
        ot_weekday_hours=_quantized(summary.ot_weekday_hours, AMOUNT_QUANTUM),
        ot_weekend_hours=_quantized(summary.ot_weekend_hours, AMOUNT_QUANTUM),
        ot_holiday_hours=_quantized(summary.ot_holiday_hours, AMOUNT_QUANTUM),
        attendance_deduct=_quantized(summary.attendance_deduct, AMOUNT_QUANTUM),
    )


def read_locked_month_summary(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: date,
    employee_id: uuid.UUID,
) -> AttendanceSource:
    """Return one employee's locked month summary and source identifiers."""
    month_start = month.replace(day=1)
    month_row = session.exec(
        select(AttendanceMonth).where(
            col(AttendanceMonth.company_id) == company_id,
            col(AttendanceMonth.month) == month_start,
        )
    ).first()
    if month_row is None:
        raise DomainError(AttendanceReadErrorCode.MONTH_MISSING, MONTH_MISSING_MESSAGE)
    if month_row.status != AttendanceMonthStatus.LOCKED:
        raise DomainError(
            AttendanceReadErrorCode.MONTH_NOT_LOCKED, MONTH_NOT_LOCKED_MESSAGE
        )
    snapshot = session.exec(
        select(AttendanceMonthSnapshot)
        .where(
            col(AttendanceMonthSnapshot.attendance_month_id) == month_row.id,
        )
        .order_by(
            col(AttendanceMonthSnapshot.version).desc(),
            col(AttendanceMonthSnapshot.id).desc(),
        )
    ).first()
    if snapshot is None:
        raise _source_inconsistent()
    summary = session.exec(
        select(AttendanceMonthSummary).where(
            col(AttendanceMonthSummary.attendance_month_id) == month_row.id,
            col(AttendanceMonthSummary.employee_id) == employee_id,
        )
    ).first()
    if summary is None:
        raise DomainError(
            AttendanceReadErrorCode.SUMMARY_MISSING, SUMMARY_MISSING_MESSAGE
        )
    if summary.calc_run_id != snapshot.calc_run_id:
        raise _source_inconsistent()
    calc_run = session.get(CalcRun, snapshot.calc_run_id)
    if calc_run is None or calc_run.attendance_month_id != month_row.id:
        raise _source_inconsistent()
    return AttendanceSource(
        attendance_month_id=month_row.id,
        attendance_snapshot_id=snapshot.id,
        attendance_snapshot_version=snapshot.version,
        attendance_calc_run_id=snapshot.calc_run_id,
        calc_version=calc_run.calc_version,
        rules_version=calc_run.rules_version,
        locked_at=snapshot.locked_at,
        values=_summary_values(summary),
    )
