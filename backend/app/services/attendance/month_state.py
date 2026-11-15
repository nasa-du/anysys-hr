"""Attendance-month row locking and editability checks.

Plan saves, roster writes, personnel sync, and adjustments all need the same
``SELECT ... FOR UPDATE`` on the month row before they touch month data.
Confirmed and locked months reject every attendance data change (spec
sections 5.6 and 8.7); the callers own the transaction.

A second concurrent calculation must fail fast with ``calc_in_progress``
instead of queueing (spec section 7.12). The transaction-level advisory lock
provides that guard; the month row lock then waits for a short non-calculation
write (such as an adjustment) to commit instead of misreporting it as a
calculation in progress.
"""

import hashlib
import uuid
from datetime import date
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import AttendanceMonthStatus
from app.models import AttendanceMonth
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.staleness import EDITABLE_MONTH_STATUSES

MONTH_CONFIRMED_MESSAGE = "考勤月份已确认，请先取消确认"
MONTH_LOCKED_MESSAGE = "考勤月份已锁定，请先解锁"
EXPANSION_BLOCKED_MESSAGE = "考勤月份已确认或锁定，无法展开排班"
CALC_IN_PROGRESS_MESSAGE = "考勤正在计算中，请稍后重试"

__all__ = [
    "CALC_IN_PROGRESS_MESSAGE",
    "EDITABLE_MONTH_STATUSES",
    "EXPANSION_BLOCKED_MESSAGE",
    "MONTH_CONFIRMED_MESSAGE",
    "MONTH_LOCKED_MESSAGE",
    "ensure_month_editable",
    "ensure_month_expandable",
    "existing_month",
    "get_or_create_month",
    "lock_month_for_calculation",
]


def _calculation_lock_key(company_id: uuid.UUID, month: date) -> int:
    digest = hashlib.sha256(
        f"attendance-calc:{company_id}:{month.isoformat()}".encode()
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def _calc_in_progress_error() -> DomainError:
    return DomainError(AttendanceErrorCode.CALC_IN_PROGRESS, CALC_IN_PROGRESS_MESSAGE)


def _first_with_lock(session: Session, statement: Any) -> AttendanceMonth | None:
    return cast(AttendanceMonth | None, session.exec(statement).first())


def lock_month_for_calculation(
    session: Session, company_id: uuid.UUID, month: date
) -> AttendanceMonth:
    """Lock one company-month for calculation or fail with ``calc_in_progress``.

    The advisory lock makes first-time row creation race-free and is released
    by the caller's rollback; the row lock remains the contract-level guard.
    """
    acquired = session.scalar(
        text("SELECT pg_try_advisory_xact_lock(:key)"),
        {"key": _calculation_lock_key(company_id, month)},
    )
    if not acquired:
        raise _calc_in_progress_error()

    statement = (
        select(AttendanceMonth)
        .where(
            col(AttendanceMonth.company_id) == company_id,
            col(AttendanceMonth.month) == month,
        )
        .with_for_update()
    )
    month_row = _first_with_lock(session, statement)
    if month_row is not None:
        return month_row

    month_row = AttendanceMonth(
        company_id=company_id,
        month=month,
        status=AttendanceMonthStatus.DRAFT,
        is_stale=True,
    )
    try:
        with session.begin_nested():
            session.add(month_row)
            session.flush()
    except IntegrityError:
        month_row = _first_with_lock(session, statement)
        if month_row is None:
            raise
    return month_row


def existing_month(
    session: Session, company_id: uuid.UUID, month: date, *, for_update: bool = False
) -> AttendanceMonth | None:
    statement = select(AttendanceMonth).where(
        col(AttendanceMonth.company_id) == company_id,
        col(AttendanceMonth.month) == month,
    )
    if for_update:
        statement = statement.with_for_update()
    return session.exec(statement).first()


def get_or_create_month(
    session: Session, company_id: uuid.UUID, month: date
) -> AttendanceMonth:
    existing = existing_month(session, company_id, month, for_update=True)
    if existing is not None:
        return existing
    month_row = AttendanceMonth(
        company_id=company_id,
        month=month,
        status=AttendanceMonthStatus.DRAFT,
        is_stale=True,
    )
    try:
        with session.begin_nested():
            session.add(month_row)
            session.flush()
    except IntegrityError:
        # Another request created the row between the select and the insert.
        existing = existing_month(session, company_id, month, for_update=True)
        if existing is None:
            raise
        return existing
    return month_row


def ensure_month_editable(month: AttendanceMonth) -> None:
    if month.status == AttendanceMonthStatus.LOCKED:
        raise DomainError(AttendanceErrorCode.MONTH_LOCKED, MONTH_LOCKED_MESSAGE)
    if month.status == AttendanceMonthStatus.CONFIRMED:
        raise DomainError(AttendanceErrorCode.MONTH_CONFIRMED, MONTH_CONFIRMED_MESSAGE)


def ensure_month_expandable(
    month: AttendanceMonth, message: str = EXPANSION_BLOCKED_MESSAGE
) -> None:
    if month.status not in EDITABLE_MONTH_STATUSES:
        raise DomainError(
            AttendanceErrorCode.SCHEDULE_EXPANSION_BLOCKED,
            message,
        )
