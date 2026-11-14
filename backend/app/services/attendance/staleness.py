"""Mark calculated attendance results as out of date.

Rules, holidays, plans, roster, and imports never recalculate automatically.
They only flag existing ``draft`` / ``calculated`` months as stale; confirmed
and locked results remain untouched (spec sections 5.6 and 8.7).
"""

import uuid

from sqlmodel import Session, col, select

from app.enums import AttendanceMonthStatus
from app.models import AttendanceMonth, get_datetime_utc

EDITABLE_MONTH_STATUSES = (
    AttendanceMonthStatus.DRAFT,
    AttendanceMonthStatus.CALCULATED,
)


def mark_company_months_stale(session: Session, company_id: uuid.UUID) -> int:
    """Flag every editable month of one company; callers own the commit."""
    months = session.exec(
        select(AttendanceMonth).where(
            col(AttendanceMonth.company_id) == company_id,
            col(AttendanceMonth.status).in_(EDITABLE_MONTH_STATUSES),
        )
    ).all()
    now = get_datetime_utc()
    for month in months:
        month.is_stale = True
        month.updated_at = now
    return len(months)


def mark_month_stale(month: AttendanceMonth) -> None:
    """Flag one editable month; callers own the commit."""
    if month.status in EDITABLE_MONTH_STATUSES:
        month.is_stale = True
        month.updated_at = get_datetime_utc()
