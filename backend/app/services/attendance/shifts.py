"""Shift template business rules: CRUD, time validation, and blockers.

Shift templates are company-level and reusable. Cross-field time rules live in
a pure validator so create and update share one code path; reference blocking
uses the shared ``BlockerQuery`` vocabulary.
"""

import uuid
from dataclasses import dataclass
from datetime import time

from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import PlanStatus
from app.models import (
    Company,
    Employee,
    Message,
    PlanDay,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
    get_datetime_utc,
)
from app.schemas_attendance.core import (
    ShiftCreate,
    ShiftPublic,
    ShiftsPublic,
    ShiftUpdate,
)
from app.services.attendance.errors import AttendanceErrorCode
from app.services.common import BlockerQuery, collect_blockers, paginate
from app.services.companies import get_company_or_404

SHIFT_NOT_FOUND_MESSAGE = "班次不存在"
COMPANY_NOT_FOUND_MESSAGE = "公司不存在"
INACTIVE_COMPANY_MESSAGE = "公司已停用，无法创建班次"
DUPLICATE_CODE_MESSAGE = "班次编码已存在"
END_AFTER_START_MESSAGE = "结束时间必须晚于开始时间"
CROSS_DAY_END_MESSAGE = "跨天班次的结束时间必须早于或等于开始时间"
BREAK_PAIR_MESSAGE = "休息开始与结束时间必须同时填写"
BREAK_RANGE_MESSAGE = "休息时间必须位于班次时间范围内，且开始时间早于结束时间"
INVALID_TIME_RANGE_BACKSTOP_MESSAGE = "班次时间设置不符合约束，请检查时间范围"
DEACTIVATE_BLOCKED_MESSAGE = "无法停用：仍有启用中的排班方案引用该班次"
REFERENCED_MESSAGE = "无法删除：仍有排班方案或排班明细引用该班次"

_SECONDS_PER_DAY = 24 * 60 * 60


@dataclass(frozen=True)
class ShiftTimeValues:
    """The cross-field time values validated together on create and update."""

    start_time: time
    end_time: time
    cross_day: bool
    break_start: time | None
    break_end: time | None
    rest_minutes: int


def _seconds(value: time) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def _span_seconds(start_time: time, end_time: time, cross_day: bool) -> int:
    span = (_seconds(end_time) - _seconds(start_time)) % _SECONDS_PER_DAY
    if cross_day and span == 0:
        return _SECONDS_PER_DAY
    return span


def _invalid_time_range(field_errors: dict[str, str], message: str) -> DomainError:
    return DomainError(
        AttendanceErrorCode.INVALID_TIME_RANGE,
        message,
        field_errors=field_errors,
    )


def validate_shift_times(values: ShiftTimeValues) -> None:
    """Validate cross-day, break, and rest-deduction rules.

    Relative positions are measured from the shift start on a 24-hour clock so
    breaks after midnight work on cross-day shifts. A break must sit strictly
    inside the shift; the rest deduction may consume the whole span but not
    make the work time negative.
    """
    start_seconds = _seconds(values.start_time)
    end_seconds = _seconds(values.end_time)

    if values.cross_day:
        if end_seconds > start_seconds:
            raise _invalid_time_range(
                {"end_time": CROSS_DAY_END_MESSAGE}, CROSS_DAY_END_MESSAGE
            )
    elif end_seconds <= start_seconds:
        raise _invalid_time_range(
            {"end_time": END_AFTER_START_MESSAGE}, END_AFTER_START_MESSAGE
        )

    span = _span_seconds(values.start_time, values.end_time, values.cross_day)

    if (values.break_start is None) != (values.break_end is None):
        missing = "break_start" if values.break_start is None else "break_end"
        field_message = (
            "请填写休息开始时间" if missing == "break_start" else "请填写休息结束时间"
        )
        raise _invalid_time_range({missing: field_message}, BREAK_PAIR_MESSAGE)

    if values.break_start is not None and values.break_end is not None:
        relative_start = (
            _seconds(values.break_start) - start_seconds
        ) % _SECONDS_PER_DAY
        relative_end = (_seconds(values.break_end) - start_seconds) % _SECONDS_PER_DAY
        if not 0 < relative_start < relative_end < span:
            raise _invalid_time_range(
                {
                    "break_start": BREAK_RANGE_MESSAGE,
                    "break_end": BREAK_RANGE_MESSAGE,
                },
                BREAK_RANGE_MESSAGE,
            )

    if values.rest_minutes * 60 > span:
        message = f"休息扣减不能超过班次时长（{span // 60} 分钟）"
        raise _invalid_time_range({"rest_minutes": message}, message)


def _duplicate_code_error() -> DomainError:
    return DomainError(
        AttendanceErrorCode.DUPLICATE_CODE,
        DUPLICATE_CODE_MESSAGE,
        field_errors={"shift_code": DUPLICATE_CODE_MESSAGE},
    )


def _field_error(code: AttendanceErrorCode, field: str, message: str) -> DomainError:
    return DomainError(code, message, field_errors={field: message})


def get_shift_or_404(session: Session, shift_id: uuid.UUID) -> Shift:
    shift = session.get(Shift, shift_id)
    if shift is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, SHIFT_NOT_FOUND_MESSAGE)
    return shift


def list_shifts(
    session: Session,
    *,
    company_id: uuid.UUID,
    keyword: str | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> ShiftsPublic:
    """List a company's shifts ordered by shift code."""
    get_company_or_404(session, company_id)

    filters: list[ColumnElement[bool]] = [col(Shift.company_id) == company_id]
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        filters.append(
            or_(
                col(Shift.shift_code).ilike(pattern),
                col(Shift.shift_name).ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(col(Shift.is_active) == is_active)

    statement = select(Shift).where(*filters).order_by(col(Shift.shift_code).asc())
    count_statement = select(func.count()).select_from(Shift).where(*filters)
    items, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return ShiftsPublic(
        data=[ShiftPublic.model_validate(shift) for shift in items],
        count=count,
    )


def get_shift(session: Session, shift_id: uuid.UUID) -> ShiftPublic:
    return ShiftPublic.model_validate(get_shift_or_404(session, shift_id))


def create_shift(session: Session, payload: ShiftCreate) -> ShiftPublic:
    company = session.get(Company, payload.company_id)
    if company is None:
        raise _field_error(
            AttendanceErrorCode.INVALID_REFERENCE,
            "company_id",
            COMPANY_NOT_FOUND_MESSAGE,
        )
    if not company.is_active:
        raise _field_error(
            AttendanceErrorCode.INACTIVE_REFERENCE,
            "company_id",
            INACTIVE_COMPANY_MESSAGE,
        )

    existing = session.exec(
        select(Shift).where(
            Shift.company_id == company.id,
            Shift.shift_code == payload.shift_code,
        )
    ).first()
    if existing is not None:
        raise _duplicate_code_error()

    validate_shift_times(
        ShiftTimeValues(
            start_time=payload.start_time,
            end_time=payload.end_time,
            cross_day=payload.cross_day,
            break_start=payload.break_start,
            break_end=payload.break_end,
            rest_minutes=payload.rest_minutes,
        )
    )

    shift = Shift(
        company_id=company.id,
        shift_code=payload.shift_code,
        shift_name=payload.shift_name,
        start_time=payload.start_time,
        end_time=payload.end_time,
        cross_day=payload.cross_day,
        break_start=payload.break_start,
        break_end=payload.break_end,
        rest_minutes=payload.rest_minutes,
        color=payload.color,
        note=payload.note,
        is_active=payload.is_active,
    )
    session.add(shift)
    try:
        session.commit()
    except IntegrityError:
        # A concurrent insert may take the code between the check and commit;
        # otherwise a check constraint rejected a time value. Do not report a
        # duplicate code when the code is actually free.
        session.rollback()
        existing = session.exec(
            select(Shift).where(
                Shift.company_id == company.id,
                Shift.shift_code == payload.shift_code,
            )
        ).first()
        if existing is not None:
            raise _duplicate_code_error()
        raise DomainError(
            AttendanceErrorCode.INVALID_TIME_RANGE,
            INVALID_TIME_RANGE_BACKSTOP_MESSAGE,
        )
    session.refresh(shift)
    return ShiftPublic.model_validate(shift)


def _plan_blocker_query(shift_id: uuid.UUID, *, active_only: bool) -> BlockerQuery:
    """Plans that reference the shift through their day rows.

    ``active_only`` implements deactivation: only enabled plans block while
    archived plans still block deletion. A plan is counted once even when it
    schedules the shift on several days.
    """
    conditions: list[ColumnElement[bool]] = [col(PlanDay.shift_id) == shift_id]
    if active_only:
        conditions.append(col(SchedulePlan.status) == PlanStatus.ENABLED)

    month_code = func.to_char(col(SchedulePlan.month), "YYYY-MM")
    return BlockerQuery(
        type="schedule_plan",
        count_statement=select(func.count(func.distinct(col(PlanDay.plan_id))))
        .select_from(PlanDay)
        .join(SchedulePlan, col(PlanDay.plan_id) == col(SchedulePlan.id))
        .where(*conditions),
        rows_statement=select(
            SchedulePlan.id,
            month_code,
            SchedulePlan.plan_name,
        )
        .select_from(PlanDay)
        .join(SchedulePlan, col(PlanDay.plan_id) == col(SchedulePlan.id))
        .where(*conditions)
        .distinct()
        .order_by(month_code.asc(), col(SchedulePlan.plan_name).asc()),
    )


def _roster_snapshot_blocker_query(shift_id: uuid.UUID) -> BlockerQuery:
    """Roster snapshots that reference the shift.

    Each roster entry is counted once; the label identifies the employee and
    date so the dialog explains which history blocks the deletion.
    """
    snapshot_entry_ids = select(RosterEntryShift.roster_entry_id).where(
        col(RosterEntryShift.shift_id) == shift_id
    )
    conditions: list[ColumnElement[bool]] = [
        col(RosterEntry.id).in_(snapshot_entry_ids)
    ]
    return BlockerQuery(
        type="roster_entry",
        count_statement=select(func.count())
        .select_from(RosterEntry)
        .where(*conditions),
        rows_statement=select(
            RosterEntry.id,
            Employee.employee_no,
            func.concat(
                Employee.name,
                " ",
                func.to_char(col(RosterEntry.work_date), "YYYY-MM-DD"),
            ),
        )
        .join(Employee, col(RosterEntry.employee_id) == col(Employee.id))
        .where(*conditions)
        .order_by(
            col(Employee.employee_no).asc(),
            col(RosterEntry.work_date).asc(),
        ),
    )


def _blocker_queries(shift_id: uuid.UUID, *, active_only: bool) -> list[BlockerQuery]:
    queries = [_plan_blocker_query(shift_id, active_only=active_only)]
    if not active_only:
        queries.append(_roster_snapshot_blocker_query(shift_id))
    return queries


def update_shift(
    session: Session, shift_id: uuid.UUID, payload: ShiftUpdate
) -> ShiftPublic:
    shift = get_shift_or_404(session, shift_id)
    data = payload.model_dump(exclude_unset=True)

    validate_shift_times(
        ShiftTimeValues(
            start_time=data.get("start_time", shift.start_time),
            end_time=data.get("end_time", shift.end_time),
            cross_day=data.get("cross_day", shift.cross_day),
            break_start=(
                data["break_start"] if "break_start" in data else shift.break_start
            ),
            break_end=data["break_end"] if "break_end" in data else shift.break_end,
            rest_minutes=data.get("rest_minutes", shift.rest_minutes),
        )
    )

    if data.get("is_active") is False and shift.is_active:
        total, blockers = collect_blockers(
            session, _blocker_queries(shift.id, active_only=True)
        )
        if total:
            raise DomainError(
                AttendanceErrorCode.DEACTIVATE_BLOCKED,
                DEACTIVATE_BLOCKED_MESSAGE,
                field_errors={"is_active": "存在启用中的排班方案"},
                blockers=blockers,
                blocker_count=total,
            )

    for field, value in data.items():
        setattr(shift, field, value)
    shift.updated_at = get_datetime_utc()

    session.add(shift)
    try:
        session.commit()
    except IntegrityError:
        # The validator mirrors the database checks; this is the backstop for
        # a constraint the service could not see. Never expose database text.
        session.rollback()
        raise DomainError(
            AttendanceErrorCode.INVALID_TIME_RANGE,
            INVALID_TIME_RANGE_BACKSTOP_MESSAGE,
        )
    session.refresh(shift)
    return ShiftPublic.model_validate(shift)


def _referenced_error(session: Session, shift_id: uuid.UUID) -> DomainError:
    queries = _blocker_queries(shift_id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    return DomainError(
        AttendanceErrorCode.REFERENCED,
        REFERENCED_MESSAGE,
        blockers=blockers,
        blocker_count=total,
    )


def delete_shift(session: Session, shift_id: uuid.UUID) -> Message:
    shift = get_shift_or_404(session, shift_id)
    queries = _blocker_queries(shift.id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    if total:
        raise DomainError(
            AttendanceErrorCode.REFERENCED,
            REFERENCED_MESSAGE,
            blockers=blockers,
            blocker_count=total,
        )

    session.delete(shift)
    try:
        session.commit()
    except IntegrityError:
        # A plan or roster snapshot appeared between the check and the delete;
        # report the current blockers rather than database text.
        session.rollback()
        raise _referenced_error(session, shift_id)
    return Message(message="班次删除成功")
