"""Versioned manual result adjustments (spec sections 4.9.4, 7.11, and 8.3.5).

An adjustment is a result-layer override, never a DELETE. Each POST creates a
new version, supersedes the previous active version in the same transaction,
and uses ``base_version`` as an optimistic lock. A version is the complete set
of overrides: fields omitted from ``adjusted_values`` fall back to the values
the calculation produced. ``original_values`` records those calculated values
so undo can submit them as a new restoring version.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import AdjustmentStatus, DayStatus
from app.models import (
    AttendanceDayResult,
    AttendanceResultAdjustment,
    Department,
    Employee,
    User,
    get_datetime_utc,
)
from app.schemas_attendance.results import (
    AttendanceAdjustmentCreate,
    AttendanceAdjustmentPublic,
    AttendanceAdjustmentsPublic,
)
from app.services.attendance.calc._common import month_bounds
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.month_state import ensure_month_editable, existing_month
from app.services.attendance.results import (
    recompute_day_deductions,
    recompute_month_summary_from_days,
)
from app.services.common import paginate
from app.services.companies import get_company_or_404

ADJUSTABLE_FIELDS: tuple[str, ...] = (
    "day_status",
    "attendance_fraction",
    "worked_minutes",
    "ot_weekday_minutes",
    "ot_weekend_minutes",
    "ot_holiday_minutes",
    "late_minutes",
    "early_minutes",
    "missing_punch_count",
    "leave_days",
    "note",
)

ADJUSTMENT_CONFLICT_MESSAGE = "调整版本已变化，请刷新后重试"
ADJUSTMENT_NOT_FOUND_MESSAGE = "人工调整不存在"
DAY_RESULT_NOT_FOUND_MESSAGE = "考勤结果不存在，请先完成计算"
EMPLOYEE_NOT_FOUND_MESSAGE = "员工不存在"
CROSS_COMPANY_MESSAGE = "不能引用其他公司的数据"

_DECIMAL_FIELDS = frozenset({"attendance_fraction", "leave_days"})
_INT_FIELDS = frozenset(
    {
        "worked_minutes",
        "ot_weekday_minutes",
        "ot_weekend_minutes",
        "ot_holiday_minutes",
        "late_minutes",
        "early_minutes",
        "missing_punch_count",
    }
)


def _json_value(value: Any) -> Any:
    """Serialize one adjustable value for a JSONB column."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, DayStatus):
        return value.value
    return value


def _python_value(field: str, value: Any) -> Any:
    """Turn a JSONB value back into the column's Python type."""
    if value is None:
        return None
    if field == "day_status":
        return value if isinstance(value, DayStatus) else DayStatus(value)
    if field in _DECIMAL_FIELDS:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    if field in _INT_FIELDS:
        return int(value)
    return value


def _adjustable_values(day: AttendanceDayResult) -> dict[str, Any]:
    return {
        field: _python_value(field, getattr(day, field)) for field in ADJUSTABLE_FIELDS
    }


def _baseline_values(
    day: AttendanceDayResult, active: AttendanceResultAdjustment | None
) -> dict[str, Any]:
    """The calculated values the new version starts from.

    The active version already overrides its keys, so those keys come from its
    ``original_values``; every other key is unadjusted on the day row.
    """
    baseline = _adjustable_values(day)
    if active is not None:
        for field in active.adjusted_values:
            baseline[field] = _python_value(field, active.original_values.get(field))
    return baseline


def _requested_values(
    payload: AttendanceAdjustmentCreate,
) -> dict[str, Any]:
    """The sparse override set, preserving an explicit ``note: null``."""
    requested = payload.adjusted_values.model_dump(exclude_unset=True)
    return {field: _python_value(field, value) for field, value in requested.items()}


def _public(
    adjustment: AttendanceResultAdjustment, adjusted_by_name: str | None
) -> AttendanceAdjustmentPublic:
    public = AttendanceAdjustmentPublic.model_validate(adjustment)
    public.adjusted_by_name = adjusted_by_name
    return public


def _user_name(user: User) -> str | None:
    return user.full_name or user.email


def _adjusted_by_names(
    session: Session, rows: list[AttendanceResultAdjustment]
) -> dict[uuid.UUID, str | None]:
    user_ids = {row.adjusted_by for row in rows}
    if not user_ids:
        return {}
    users = session.exec(select(User).where(col(User.id).in_(user_ids))).all()
    return {user.id: _user_name(user) for user in users}


def list_adjustments(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str | None,
    employee_id: uuid.UUID | None,
    work_date: date | None,
    status: AdjustmentStatus | None,
    skip: int,
    limit: int,
) -> AttendanceAdjustmentsPublic:
    """List versions for one company, newest day and newest version first."""
    get_company_or_404(session, company_id)
    filters: list[ColumnElement[bool]] = [
        col(AttendanceResultAdjustment.company_id) == company_id
    ]
    if month is not None:
        start, end = month_bounds(date.fromisoformat(f"{month}-01"))
        filters.extend(
            [
                col(AttendanceResultAdjustment.work_date) >= start,
                col(AttendanceResultAdjustment.work_date) <= end,
            ]
        )
    if employee_id is not None:
        filters.append(col(AttendanceResultAdjustment.employee_id) == employee_id)
    if work_date is not None:
        filters.append(col(AttendanceResultAdjustment.work_date) == work_date)
    if status is not None:
        filters.append(col(AttendanceResultAdjustment.status) == status)

    statement = (
        select(AttendanceResultAdjustment)
        .where(*filters)
        .order_by(
            col(AttendanceResultAdjustment.work_date).desc(),
            col(AttendanceResultAdjustment.employee_id).asc(),
            col(AttendanceResultAdjustment.version).desc(),
            col(AttendanceResultAdjustment.id).desc(),
        )
    )
    count_statement = (
        select(func.count()).select_from(AttendanceResultAdjustment).where(*filters)
    )
    rows, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    names = _adjusted_by_names(session, rows)
    return AttendanceAdjustmentsPublic(
        data=[_public(row, names.get(row.adjusted_by)) for row in rows],
        count=count,
    )


def get_adjustment(
    session: Session, adjustment_id: uuid.UUID
) -> AttendanceAdjustmentPublic:
    adjustment = session.get(AttendanceResultAdjustment, adjustment_id)
    if adjustment is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, ADJUSTMENT_NOT_FOUND_MESSAGE)
    names = _adjusted_by_names(session, [adjustment])
    return _public(adjustment, names.get(adjustment.adjusted_by))


def reapply_active_adjustments(session: Session, *, month_id: uuid.UUID) -> None:
    """Replay active versions onto fresh results after a calculation.

    The recorded original values and ``calc_run_id`` stay as the audit trail of
    when the adjustment was made; only the override is replayed. A version
    whose day is no longer in the result set becomes ``orphaned`` and is
    retained (spec section 7.11). Callers own the transaction.
    """
    adjustments = list(
        session.exec(
            select(AttendanceResultAdjustment).where(
                col(AttendanceResultAdjustment.attendance_month_id) == month_id,
                col(AttendanceResultAdjustment.status) == AdjustmentStatus.ACTIVE,
            )
        ).all()
    )
    if not adjustments:
        return
    days = session.exec(
        select(AttendanceDayResult).where(
            col(AttendanceDayResult.attendance_month_id) == month_id
        )
    ).all()
    by_key = {(day.employee_id, day.work_date): day for day in days}
    affected_employees: set[uuid.UUID] = set()
    now = get_datetime_utc()

    for adjustment in adjustments:
        day = by_key.get((adjustment.employee_id, adjustment.work_date))
        if day is None:
            adjustment.status = AdjustmentStatus.ORPHANED
            session.add(adjustment)
            continue
        applied = {
            field: _python_value(field, value)
            for field, value in adjustment.adjusted_values.items()
        }
        for field, value in applied.items():
            setattr(day, field, value)
        day.is_adjusted = True
        day.adjustment_id = adjustment.id
        day.updated_at = now
        session.add(day)
        recompute_day_deductions(session, day)
        affected_employees.add(adjustment.employee_id)

    for employee_id in affected_employees:
        recompute_month_summary_from_days(
            session, month_id=month_id, employee_id=employee_id
        )


def create_adjustment(
    session: Session,
    payload: AttendanceAdjustmentCreate,
    *,
    operator: User,
) -> AttendanceAdjustmentPublic:
    """Create one adjustment version; ``base_version`` guards lost updates."""
    get_company_or_404(session, payload.company_id)

    employee = session.get(Employee, payload.employee_id)
    if employee is None:
        raise DomainError(
            AttendanceErrorCode.INVALID_REFERENCE,
            EMPLOYEE_NOT_FOUND_MESSAGE,
            field_errors={"employee_id": EMPLOYEE_NOT_FOUND_MESSAGE},
        )
    department = session.get(Department, employee.dept_id)
    if department is None:
        raise DomainError(
            AttendanceErrorCode.INVALID_REFERENCE,
            EMPLOYEE_NOT_FOUND_MESSAGE,
            field_errors={"employee_id": EMPLOYEE_NOT_FOUND_MESSAGE},
        )
    if department.company_id != payload.company_id:
        raise DomainError(
            AttendanceErrorCode.CROSS_COMPANY,
            CROSS_COMPANY_MESSAGE,
            field_errors={"employee_id": CROSS_COMPANY_MESSAGE},
        )

    month_row = existing_month(
        session, payload.company_id, payload.work_date.replace(day=1), for_update=True
    )
    if month_row is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, DAY_RESULT_NOT_FOUND_MESSAGE)
    ensure_month_editable(month_row)

    day = session.exec(
        select(AttendanceDayResult)
        .where(
            col(AttendanceDayResult.attendance_month_id) == month_row.id,
            col(AttendanceDayResult.employee_id) == payload.employee_id,
            col(AttendanceDayResult.work_date) == payload.work_date,
        )
        .with_for_update()
    ).first()
    if day is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, DAY_RESULT_NOT_FOUND_MESSAGE)

    active = session.exec(
        select(AttendanceResultAdjustment)
        .where(
            col(AttendanceResultAdjustment.attendance_month_id) == month_row.id,
            col(AttendanceResultAdjustment.employee_id) == payload.employee_id,
            col(AttendanceResultAdjustment.work_date) == payload.work_date,
            col(AttendanceResultAdjustment.status) == AdjustmentStatus.ACTIVE,
        )
        .with_for_update()
    ).first()
    current_version = active.version if active is not None else 0
    if payload.base_version != current_version:
        raise DomainError(
            AttendanceErrorCode.ADJUSTMENT_CONFLICT,
            ADJUSTMENT_CONFLICT_MESSAGE,
            field_errors={"base_version": ADJUSTMENT_CONFLICT_MESSAGE},
        )

    baseline = _baseline_values(day, active)
    requested = _requested_values(payload)
    original_values = {field: _json_value(baseline[field]) for field in requested}
    adjusted_values = {field: _json_value(value) for field, value in requested.items()}

    max_version = session.exec(
        select(func.max(AttendanceResultAdjustment.version)).where(
            col(AttendanceResultAdjustment.attendance_month_id) == month_row.id,
            col(AttendanceResultAdjustment.employee_id) == payload.employee_id,
            col(AttendanceResultAdjustment.work_date) == payload.work_date,
        )
    ).one()
    now = get_datetime_utc()
    if active is not None:
        active.status = AdjustmentStatus.SUPERSEDED
        session.add(active)

    adjustment = AttendanceResultAdjustment(
        company_id=payload.company_id,
        attendance_month_id=month_row.id,
        employee_id=payload.employee_id,
        work_date=payload.work_date,
        version=(max_version or 0) + 1,
        status=AdjustmentStatus.ACTIVE,
        original_values=original_values,
        adjusted_values=adjusted_values,
        reason=payload.reason,
        adjusted_by=operator.id,
        adjusted_at=now,
        calc_run_id=day.calc_run_id,
    )
    session.add(adjustment)
    session.flush()

    for field in ADJUSTABLE_FIELDS:
        setattr(day, field, baseline[field])
    for field, value in requested.items():
        setattr(day, field, value)
    day.is_adjusted = True
    day.adjustment_id = adjustment.id
    day.updated_at = now
    session.add(day)
    recompute_day_deductions(session, day)

    recompute_month_summary_from_days(
        session, month_id=month_row.id, employee_id=payload.employee_id
    )
    session.commit()
    session.refresh(adjustment)
    return _public(adjustment, _user_name(operator))
