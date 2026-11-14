"""Company holiday calendar: CRUD and copy-from-previous-year.

Holidays are company-scoped. ``(company_id, date)`` is unique and ``date`` is
immutable. Changes only mark ``draft`` / ``calculated`` months stale; confirmed
and locked results never change (spec sections 4.5, 5.7, and 8.3.7). Excel
bulk import is intentionally not provided.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import ColumnElement, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import DayType, HolidayDayType
from app.models import Holiday, Message, get_datetime_utc
from app.schemas_attendance.core import (
    HolidayCopyConflict,
    HolidayCopyCreate,
    HolidayCopyPreview,
    HolidayCopyRequest,
    HolidayCopyResult,
    HolidayCreate,
    HolidayPublic,
    HolidaysPublic,
    HolidayUpdate,
)
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.staleness import mark_company_months_stale
from app.services.common import paginate
from app.services.companies import get_company_or_404

HOLIDAY_NOT_FOUND_MESSAGE = "节假日不存在"
DUPLICATE_HOLIDAY_MESSAGE = "该日期已存在节假日记录"
HOLIDAY_CONFLICT_MESSAGE = "目标年份存在冲突的节假日，请确认覆盖后再复制"


@dataclass(frozen=True)
class _CopyPlan:
    """A resolved copy: dates to create, date pairs to overwrite, skipped."""

    creates: list[tuple[date, Holiday]]
    conflicts: list[tuple[Holiday, Holiday]]
    skipped: int


def _duplicate_holiday_error() -> DomainError:
    return DomainError(
        AttendanceErrorCode.DUPLICATE_HOLIDAY,
        DUPLICATE_HOLIDAY_MESSAGE,
        field_errors={"date": DUPLICATE_HOLIDAY_MESSAGE},
    )


def _holiday_conflict_error(conflict_count: int) -> DomainError:
    return DomainError(
        AttendanceErrorCode.HOLIDAY_CONFLICT,
        f"{HOLIDAY_CONFLICT_MESSAGE}（{conflict_count} 个冲突日期）",
        field_errors={"overwrite": "目标年份已有节假日，请勾选覆盖后复制"},
    )


def get_holiday_or_404(session: Session, holiday_id: uuid.UUID) -> Holiday:
    holiday = session.get(Holiday, holiday_id)
    if holiday is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, HOLIDAY_NOT_FOUND_MESSAGE)
    return holiday


def list_holidays(
    session: Session,
    *,
    company_id: uuid.UUID,
    year: int | None,
    skip: int,
    limit: int,
) -> HolidaysPublic:
    """List a company's calendar ordered by date."""
    get_company_or_404(session, company_id)

    filters: list[ColumnElement[bool]] = [col(Holiday.company_id) == company_id]
    if year is not None:
        filters.extend(
            [
                col(Holiday.date) >= date(year, 1, 1),
                col(Holiday.date) <= date(year, 12, 31),
            ]
        )

    statement = select(Holiday).where(*filters).order_by(col(Holiday.date).asc())
    count_statement = select(func.count()).select_from(Holiday).where(*filters)
    items, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return HolidaysPublic(
        data=[HolidayPublic.model_validate(holiday) for holiday in items],
        count=count,
    )


def create_holiday(session: Session, payload: HolidayCreate) -> HolidayPublic:
    get_company_or_404(session, payload.company_id)

    existing = session.exec(
        select(Holiday).where(
            col(Holiday.company_id) == payload.company_id,
            col(Holiday.date) == payload.date,
        )
    ).first()
    if existing is not None:
        raise _duplicate_holiday_error()

    holiday = Holiday(
        company_id=payload.company_id,
        date=payload.date,
        name=payload.name,
        day_type=payload.day_type,
        note=payload.note,
    )
    # Mark before adding the new row: the stale-marking query triggers an
    # autoflush, and a concurrent duplicate must be caught by the commit path
    # below rather than escaping from this query.
    mark_company_months_stale(session, payload.company_id)
    session.add(holiday)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_holiday_error()
    session.refresh(holiday)
    return HolidayPublic.model_validate(holiday)


def update_holiday(
    session: Session, holiday_id: uuid.UUID, payload: HolidayUpdate
) -> HolidayPublic:
    holiday = get_holiday_or_404(session, holiday_id)
    data = payload.model_dump(exclude_unset=True)
    changed = any(getattr(holiday, field) != value for field, value in data.items())

    for field, value in data.items():
        setattr(holiday, field, value)
    if changed:
        holiday.updated_at = get_datetime_utc()
        mark_company_months_stale(session, holiday.company_id)

    session.add(holiday)
    session.commit()
    session.refresh(holiday)
    return HolidayPublic.model_validate(holiday)


def delete_holiday(session: Session, holiday_id: uuid.UUID) -> Message:
    holiday = get_holiday_or_404(session, holiday_id)
    company_id = holiday.company_id
    session.delete(holiday)
    mark_company_months_stale(session, company_id)
    session.commit()
    return Message(message="节假日删除成功")


def resolve_day_type(
    day: date, holiday_day_type: HolidayDayType | None = None
) -> DayType:
    """Deterministic day type: adjusted workday > holiday > weekend.

    The same precedence is used by the roster calendar, imports, and the
    calculation kernel (spec sections 5.7 and 7.2).
    """
    if holiday_day_type == HolidayDayType.ADJUSTED_WORKDAY:
        return DayType.WORKDAY
    if holiday_day_type == HolidayDayType.HOLIDAY:
        return DayType.HOLIDAY
    if day.weekday() >= 5:
        return DayType.WEEKEND
    return DayType.WORKDAY


def _mapped_date(source: date, target_year: int) -> date | None:
    """Map a month/day to another year; February 29 is skipped if invalid."""
    try:
        return source.replace(year=target_year)
    except ValueError:
        return None


def _source_holidays(
    session: Session, company_id: uuid.UUID, source_year: int
) -> list[Holiday]:
    return list(
        session.exec(
            select(Holiday)
            .where(
                col(Holiday.company_id) == company_id,
                col(Holiday.date) >= date(source_year, 1, 1),
                col(Holiday.date) <= date(source_year, 12, 31),
            )
            .order_by(col(Holiday.date).asc())
        ).all()
    )


def _target_holidays(
    session: Session, company_id: uuid.UUID, target_year: int
) -> dict[date, Holiday]:
    rows = session.exec(
        select(Holiday).where(
            col(Holiday.company_id) == company_id,
            col(Holiday.date) >= date(target_year, 1, 1),
            col(Holiday.date) <= date(target_year, 12, 31),
        )
    ).all()
    return {holiday.date: holiday for holiday in rows}


def _copy_plan(
    session: Session,
    company_id: uuid.UUID,
    request: HolidayCopyRequest,
) -> _CopyPlan:
    sources = _source_holidays(session, company_id, request.source_year)
    target_by_date = _target_holidays(session, company_id, request.target_year)

    creates: list[tuple[date, Holiday]] = []
    conflicts: list[tuple[Holiday, Holiday]] = []
    skipped = 0
    for source in sources:
        mapped = _mapped_date(source.date, request.target_year)
        if mapped is None:
            skipped += 1
            continue
        existing = target_by_date.get(mapped)
        if existing is None:
            creates.append((mapped, source))
        else:
            conflicts.append((existing, source))
    return _CopyPlan(creates=creates, conflicts=conflicts, skipped=skipped)


def preview_copy_year(
    session: Session, company_id: uuid.UUID, request: HolidayCopyRequest
) -> HolidayCopyPreview:
    get_company_or_404(session, company_id)
    plan = _copy_plan(session, company_id, request)
    return HolidayCopyPreview(
        create_count=len(plan.creates),
        conflict_count=len(plan.conflicts),
        creates=[
            HolidayCopyCreate(
                date=mapped,
                name=source.name,
                day_type=source.day_type,
            )
            for mapped, source in plan.creates
        ],
        conflicts=[
            HolidayCopyConflict(
                date=existing.date,
                name=source.name,
                existing_name=existing.name,
            )
            for existing, source in plan.conflicts
        ],
    )


def copy_year(
    session: Session, company_id: uuid.UUID, request: HolidayCopyRequest
) -> HolidayCopyResult:
    """Copy same month/day rows from the source year into the target year."""
    get_company_or_404(session, company_id)
    plan = _copy_plan(session, company_id, request)

    if plan.conflicts and not request.overwrite:
        raise _holiday_conflict_error(len(plan.conflicts))

    updated = 0
    if request.overwrite:
        for existing, source in plan.conflicts:
            if (
                existing.name != source.name
                or existing.day_type != source.day_type
                or existing.note != source.note
            ):
                existing.name = source.name
                existing.day_type = source.day_type
                existing.note = source.note
                existing.updated_at = get_datetime_utc()
                updated += 1

    # Mark before adding rows: stale marking runs a query and would otherwise
    # autoflush the new holidays outside the IntegrityError backstop below.
    # A repeat copy that changes nothing must not mark an editable month stale.
    if plan.creates or updated:
        mark_company_months_stale(session, company_id)

    for mapped, source in plan.creates:
        session.add(
            Holiday(
                company_id=company_id,
                date=mapped,
                name=source.name,
                day_type=source.day_type,
                note=source.note,
            )
        )

    try:
        session.commit()
    except IntegrityError:
        # A concurrent copy created one of the target dates between the plan
        # and the commit; report the documented conflict instead of DB text.
        session.rollback()
        raise _holiday_conflict_error(len(plan.conflicts) or len(plan.creates))

    return HolidayCopyResult(
        created=len(plan.creates), updated=updated, skipped=plan.skipped
    )
