"""Payroll and detail CSV exports (spec sections 7.13 and 8.3.8).

Exports are read-only projections of persisted results. They never write
attendance or payroll tables, are not persisted to disk, and always stream a
UTF-8 BOM. String cells that could be interpreted as spreadsheet formulas are
prefixed with a single quote; numeric cells stay untouched.
"""

import csv
import io
import json
import uuid
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, select

from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonth,
    AttendanceMonthSummary,
    Department,
    Employee,
)
from app.schemas_attendance.exports import (
    DETAIL_COLUMNS,
    PAYROLL_COLUMNS,
    escape_csv_cell,
)
from app.schemas_attendance.results import derive_is_abnormal
from app.services.attendance.displays import employee_display_map
from app.services.attendance.expansion import month_bounds
from app.services.attendance.month_state import existing_month
from app.services.companies import get_company_or_404

DAY_QUANTUM = Decimal("0.1")
AMOUNT_QUANTUM = Decimal("0.01")

__all__ = [
    "detail_csv",
    "payroll_csv",
    "payroll_rows",
]


def _quantized(value: Any, quantum: Decimal) -> Decimal:
    if value is None:
        return Decimal(0).quantize(quantum)
    return Decimal(str(value)).quantize(quantum)


def csv_chunks(columns: tuple[str, ...], rows: list[list[Any]]) -> Iterator[str]:
    """Yield a BOM-prefixed CSV document one row at a time.

    The first chunk carries the BOM and header; each later chunk is one row.
    String cells are formula-safe, numeric cells stay untouched.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(columns)
    yield "\ufeff" + buffer.getvalue()
    for row in rows:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow([escape_csv_cell(value) for value in row])
        yield buffer.getvalue()


def _month_summaries(
    session: Session, month_row: AttendanceMonth
) -> list[AttendanceMonthSummary]:
    return list(
        session.exec(
            select(AttendanceMonthSummary)
            .join(
                Employee,
                col(AttendanceMonthSummary.employee_id) == col(Employee.id),
            )
            .where(col(AttendanceMonthSummary.attendance_month_id) == month_row.id)
            .order_by(
                col(Employee.employee_no).asc(),
                col(AttendanceMonthSummary.id).asc(),
            )
        ).all()
    )


def _payroll_values(
    summary: AttendanceMonthSummary,
    *,
    company_name: str,
    month_text: str,
    display: tuple[Employee, Department] | None,
) -> list[Any]:
    employee, department = display if display is not None else (None, None)
    return [
        month_text,
        company_name,
        employee.employee_no if employee else None,
        employee.name if employee else None,
        department.dept_name if department else None,
        _quantized(summary.weekday_full, DAY_QUANTUM),
        _quantized(summary.weekend_full, DAY_QUANTUM),
        _quantized(summary.weekday_attended, DAY_QUANTUM),
        _quantized(summary.weekend_attended, DAY_QUANTUM),
        _quantized(summary.paid_leave_days, DAY_QUANTUM),
        _quantized(summary.ot_weekday_hours, AMOUNT_QUANTUM),
        _quantized(summary.ot_weekend_hours, AMOUNT_QUANTUM),
        _quantized(summary.ot_holiday_hours, AMOUNT_QUANTUM),
        _quantized(summary.attendance_deduct, AMOUNT_QUANTUM),
    ]


def _payroll_rows_for_month(
    session: Session, month_row: AttendanceMonth, company_name: str
) -> list[list[Any]]:
    summaries = _month_summaries(session, month_row)
    displays = employee_display_map(
        session, {summary.employee_id for summary in summaries}
    )
    month_text = month_row.month.strftime("%Y-%m")
    return [
        _payroll_values(
            summary,
            company_name=company_name,
            month_text=month_text,
            display=displays.get(summary.employee_id),
        )
        for summary in summaries
    ]


def payroll_rows(
    session: Session, *, company_id: uuid.UUID, month: date
) -> list[list[Any]]:
    """Return payroll rows in the fixed 14-column order; empty when uncalculated."""
    company = get_company_or_404(session, company_id)
    month_row = existing_month(session, company_id, month.replace(day=1))
    if month_row is None:
        return []
    return _payroll_rows_for_month(session, month_row, company.company_name)


def payroll_csv(
    session: Session, *, company_id: uuid.UUID, month: date
) -> Iterator[str]:
    """Stream the 14-column payroll CSV; a month with no results is header-only."""
    return csv_chunks(
        PAYROLL_COLUMNS,
        payroll_rows(session, company_id=company_id, month=month),
    )


def _common_values(
    *,
    record_type: str,
    month_text: str,
    company_name: str,
    company_id: uuid.UUID,
    attendance_month_id: uuid.UUID | None,
    employee_id: uuid.UUID,
    display: tuple[Employee, Department] | None,
    work_date: date | None,
    calc_run_id: uuid.UUID,
) -> dict[str, Any]:
    employee, department = display if display is not None else (None, None)
    return {
        "record_type": record_type,
        "attendance_month": month_text,
        "company_name": company_name,
        "company_id": company_id,
        "attendance_month_id": attendance_month_id,
        "employee_no": employee.employee_no if employee else None,
        "employee_name": employee.name if employee else None,
        "department_name": department.dept_name if department else None,
        "employee_id": employee_id,
        "work_date": work_date,
        "calc_run_id": calc_run_id,
    }


def _summary_values(
    summary: AttendanceMonthSummary,
    *,
    month_text: str,
    company_name: str,
    display: tuple[Employee, Department] | None,
) -> dict[str, Any]:
    values = _common_values(
        record_type="month_summary",
        month_text=month_text,
        company_name=company_name,
        company_id=summary.company_id,
        attendance_month_id=summary.attendance_month_id,
        employee_id=summary.employee_id,
        display=display,
        work_date=None,
        calc_run_id=summary.calc_run_id,
    )
    values.update(
        {
            "month_summary_id": summary.id,
            "weekday_full": summary.weekday_full,
            "weekend_full": summary.weekend_full,
            "weekday_attended": summary.weekday_attended,
            "weekend_attended": summary.weekend_attended,
            "paid_leave_days": summary.paid_leave_days,
            "unpaid_leave_days": summary.unpaid_leave_days,
            "comp_leave_days": summary.comp_leave_days,
            "trip_days": summary.trip_days,
            "ot_weekday_minutes": summary.ot_weekday_minutes,
            "ot_weekend_minutes": summary.ot_weekend_minutes,
            "ot_holiday_minutes": summary.ot_holiday_minutes,
            "ot_weekday_hours": summary.ot_weekday_hours,
            "ot_weekend_hours": summary.ot_weekend_hours,
            "ot_holiday_hours": summary.ot_holiday_hours,
            "comp_leave_used_hours": summary.comp_leave_used_hours,
            "comp_offset_unused_minutes": summary.comp_offset_unused_minutes,
            "late_count": summary.late_count,
            "late_minutes": summary.late_minutes,
            "early_count": summary.early_count,
            "early_minutes": summary.early_minutes,
            "missing_punch_count": summary.missing_punch_count,
            "absent_days": summary.absent_days,
            "worked_minutes": summary.worked_minutes,
            "attendance_deduct": summary.attendance_deduct,
            "is_adjusted": summary.is_adjusted,
            "calc_version": summary.calc_version,
            "rules_version": summary.rules_version,
            "month_summary_created_at": summary.created_at,
        }
    )
    return values


def _day_values(
    day: AttendanceDayResult,
    *,
    month_text: str,
    company_name: str,
    display: tuple[Employee, Department] | None,
) -> dict[str, Any]:
    values = _common_values(
        record_type="day_result",
        month_text=month_text,
        company_name=company_name,
        company_id=day.company_id,
        attendance_month_id=day.attendance_month_id,
        employee_id=day.employee_id,
        display=display,
        work_date=day.work_date,
        calc_run_id=day.calc_run_id,
    )
    values.update(
        {
            "day_id": day.id,
            "day_type": day.day_type,
            "roster_state": day.roster_state,
            "day_status": day.day_status,
            "day_flags": json.dumps(day.day_flags, ensure_ascii=False),
            "is_abnormal": derive_is_abnormal(day.day_status, day.day_flags),
            "day_attendance_fraction": day.attendance_fraction,
            "day_scheduled_minutes": day.scheduled_minutes,
            "day_worked_minutes": day.worked_minutes,
            "day_late_minutes": day.late_minutes,
            "day_early_minutes": day.early_minutes,
            "day_late_count": day.late_count,
            "day_early_count": day.early_count,
            "day_missing_punch_count": day.missing_punch_count,
            "day_leave_kind": day.leave_kind,
            "day_leave_days": day.leave_days,
            "day_paid_leave_days": day.paid_leave_days,
            "day_unpaid_leave_days": day.unpaid_leave_days,
            "day_comp_leave_days": day.comp_leave_days,
            "day_trip_kind": day.trip_kind,
            "day_trip_fraction": day.trip_fraction,
            "day_ot_weekday_minutes": day.ot_weekday_minutes,
            "day_ot_weekend_minutes": day.ot_weekend_minutes,
            "day_ot_holiday_minutes": day.ot_holiday_minutes,
            "day_comp_offset_minutes": day.comp_offset_minutes,
            "day_comp_offset_unused_minutes": day.comp_offset_unused_minutes,
            "day_absent_deduct_amount": day.absent_deduct_amount,
            "day_late_deduct_amount": day.late_deduct_amount,
            "day_early_deduct_amount": day.early_deduct_amount,
            "day_missing_punch_deduct_amount": day.missing_punch_deduct_amount,
            "day_deduction_total": day.deduction_total,
            "day_is_adjusted": day.is_adjusted,
            "day_adjustment_id": day.adjustment_id,
            "day_note": day.note,
            "day_created_at": day.created_at,
            "day_updated_at": day.updated_at,
        }
    )
    return values


def _shift_values(
    shift: AttendanceDayShiftResult,
    *,
    month_text: str,
    company_name: str,
    attendance_month_id: uuid.UUID,
    display: tuple[Employee, Department] | None,
) -> dict[str, Any]:
    values = _common_values(
        record_type="shift_result",
        month_text=month_text,
        company_name=company_name,
        company_id=shift.company_id,
        attendance_month_id=attendance_month_id,
        employee_id=shift.employee_id,
        display=display,
        work_date=shift.work_date,
        calc_run_id=shift.calc_run_id,
    )
    values.update(
        {
            "shift_result_id": shift.id,
            "shift_day_result_id": shift.day_result_id,
            "shift_id": shift.shift_id,
            "shift_seq": shift.seq,
            "shift_code": shift.shift_code,
            "shift_name": shift.shift_name,
            "shift_start_time": shift.start_time,
            "shift_end_time": shift.end_time,
            "shift_cross_day": shift.cross_day,
            "shift_break_start": shift.break_start,
            "shift_break_end": shift.break_end,
            "shift_rest_minutes": shift.rest_minutes,
            "shift_status": shift.shift_status,
            "shift_flags": json.dumps(shift.shift_flags, ensure_ascii=False),
            "shift_punch_in_at": shift.punch_in_at,
            "shift_punch_out_at": shift.punch_out_at,
            "shift_break_out_at": shift.break_out_at,
            "shift_break_in_at": shift.break_in_at,
            "shift_scheduled_minutes": shift.scheduled_minutes,
            "shift_worked_minutes": shift.worked_minutes,
            "shift_late_minutes": shift.late_minutes,
            "shift_early_minutes": shift.early_minutes,
            "shift_missing_punch_count": shift.missing_punch_count,
            "shift_ot_minutes": shift.ot_minutes,
            "shift_comp_offset_minutes": shift.comp_offset_minutes,
            "shift_leave_days": shift.leave_days,
            "shift_note": shift.note,
        }
    )
    return values


def detail_rows(
    session: Session, *, company_id: uuid.UUID, month: date
) -> list[dict[str, Any]]:
    """Union month-summary, day-result, and shift-result rows for one month."""
    company = get_company_or_404(session, company_id)
    month_start = month.replace(day=1)
    month_row = existing_month(session, company_id, month_start)
    if month_row is None:
        return []

    month_text = month_row.month.strftime("%Y-%m")
    start, end = month_bounds(month_start)
    summaries = _month_summaries(session, month_row)
    days = list(
        session.exec(
            select(AttendanceDayResult)
            .where(col(AttendanceDayResult.attendance_month_id) == month_row.id)
            .order_by(
                col(AttendanceDayResult.work_date).asc(),
                col(AttendanceDayResult.employee_id).asc(),
            )
        ).all()
    )
    shifts = list(
        session.exec(
            select(AttendanceDayShiftResult)
            .where(
                col(AttendanceDayShiftResult.company_id) == company_id,
                col(AttendanceDayShiftResult.work_date) >= start,
                col(AttendanceDayShiftResult.work_date) <= end,
            )
            .order_by(
                col(AttendanceDayShiftResult.work_date).asc(),
                col(AttendanceDayShiftResult.employee_id).asc(),
                col(AttendanceDayShiftResult.seq).asc(),
            )
        ).all()
    )
    employee_ids = (
        {summary.employee_id for summary in summaries}
        | {day.employee_id for day in days}
        | {shift.employee_id for shift in shifts}
    )
    displays = employee_display_map(session, employee_ids)
    day_month_ids = {day.id: day.attendance_month_id for day in days}

    rows: list[dict[str, Any]] = [
        _summary_values(
            summary,
            month_text=month_text,
            company_name=company.company_name,
            display=displays.get(summary.employee_id),
        )
        for summary in summaries
    ]
    rows.extend(
        _day_values(
            day,
            month_text=month_text,
            company_name=company.company_name,
            display=displays.get(day.employee_id),
        )
        for day in days
    )
    rows.extend(
        _shift_values(
            shift,
            month_text=month_text,
            company_name=company.company_name,
            attendance_month_id=day_month_ids.get(shift.day_result_id, month_row.id),
            display=displays.get(shift.employee_id),
        )
        for shift in shifts
    )
    return rows


def detail_csv(
    session: Session, *, company_id: uuid.UUID, month: date
) -> Iterator[str]:
    """Stream the union detail CSV; a month with no results is header-only."""
    rows = detail_rows(session, company_id=company_id, month=month)
    return csv_chunks(
        DETAIL_COLUMNS,
        [[row.get(column) for column in DETAIL_COLUMNS] for row in rows],
    )
