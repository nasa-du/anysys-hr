"""Roster entry inspection and manual scheduling (spec sections 4.4, 5.3-5.4).

The roster is the expanded, per-employee daily schedule. Reads complete the
month calendar with the API-only ``unscheduled`` state; the entry list returns
only persisted rows. Manual exceptions are ``roster_entry`` rows with
``source = manual``: they override plan rows, survive every re-expansion, and
restore the current plan resolution when deleted. Personnel sync is a full
company-month re-expansion that reports employee- and entry-level changes
before applying everything in one transaction.
"""

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Protocol

from sqlalchemy import ColumnElement, delete, func, or_
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import (
    AttendanceMonthStatus,
    DayType,
    HolidayDayType,
    RosterSource,
    RosterState,
)
from app.models import (
    AttendanceMonth,
    Department,
    Employee,
    Holiday,
    Message,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
    get_datetime_utc,
)
from app.schemas_attendance.common import EmployeeDisplay
from app.schemas_attendance.scheduling import (
    EmployeeRosterCalendarPublic,
    PersonnelSyncPreview,
    PersonnelSyncRequest,
    PersonnelSyncResult,
    RosterCalendarDay,
    RosterDayEmployee,
    RosterDayPublic,
    RosterEmployeeSummariesPublic,
    RosterEmployeeSummaryPublic,
    RosterEntriesPublic,
    RosterEntryBatchRequest,
    RosterEntryBatchResult,
    RosterEntryCreate,
    RosterEntryPublic,
    RosterEntryShiftPublic,
    RosterEntryUpdate,
    RosterEntryUpsert,
    RosterMonthDayPublic,
    RosterMonthPlanPublic,
    RosterMonthPublic,
    ShiftCountPublic,
)
from app.services.attendance import expansion
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.holidays import resolve_day_type
from app.services.attendance.month_state import (
    MONTH_CONFIRMED_MESSAGE,
    MONTH_LOCKED_MESSAGE,
)
from app.services.attendance.month_state import (
    ensure_month_editable as _ensure_month_editable,
)
from app.services.attendance.month_state import (
    ensure_month_expandable as _ensure_month_expandable,
)
from app.services.attendance.month_state import (
    existing_month as _existing_month,
)
from app.services.attendance.month_state import (
    get_or_create_month as _get_or_create_month,
)
from app.services.attendance.staleness import (
    EDITABLE_MONTH_STATUSES,
    mark_month_stale,
)
from app.services.common import paginate
from app.services.companies import get_company_or_404

__all__ = [
    "batch_entries",
    "create_roster_entry",
    "delete_roster_entry",
    "get_roster_entry",
    "list_roster_entries",
    "read_employee_calendar",
    "read_roster_day",
    "read_roster_employees",
    "read_roster_month",
    "sync_personnel",
    "sync_preview",
    "update_roster_entry",
]

ROSTER_ENTRY_NOT_FOUND_MESSAGE = "排班明细不存在"
EMPLOYEE_NOT_FOUND_MESSAGE = "员工不存在"
DEPARTMENT_NOT_FOUND_MESSAGE = "部门不存在"
CROSS_COMPANY_MESSAGE = "不能引用其他公司的数据"
EMPLOYEE_OUT_OF_RANGE_MESSAGE = "员工不在该日期的任职期间内"
SYNC_BLOCKED_MESSAGE = "考勤月份已确认或锁定，无法同步人员"
NOT_MANUAL_MESSAGE = "方案生成的排班明细不可修改，请创建人工例外"
STATE_SHIFTS_MESSAGE = "「上班」至少需要一个班次，「休息」不能包含班次"
SHIFT_MISSING_MESSAGE = "班次不存在"
SHIFT_INACTIVE_MESSAGE = "班次已停用，无法排班"
BATCH_INVALID_MESSAGE = "批量调整校验失败，请修正后重试"
DUPLICATE_DAY_MESSAGE = "同一员工同一天只能出现一条排班明细"
DUPLICATE_SHIFT_MESSAGE = "同一天不能重复排同一班次"
DUPLICATE_SEQ_MESSAGE = "同一天同一序号只能有一个班次"
DELETE_NOT_FOUND_MESSAGE = "要删除的排班明细不存在"
DELETE_NOT_MANUAL_MESSAGE = "只能删除人工例外"
DELETE_DUPLICATE_MESSAGE = "同一条排班明细不能重复删除"
SAME_PRECISION_MESSAGE = "同精确度范围存在重复方案，请检查排班数据"


# ---------------------------------------------------------------------------
# Shared helpers: months, employees, public shapes
# ---------------------------------------------------------------------------


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _month_string(month: date) -> str:
    return month.strftime("%Y-%m")


def _month_string_start(value: str) -> date:
    return date(int(value[:4]), int(value[5:7]), 1)


def _employee_department(session: Session, employee: Employee) -> Department:
    department = session.get(Department, employee.dept_id)
    if department is None:
        raise DomainError(
            AttendanceErrorCode.INVALID_REFERENCE, DEPARTMENT_NOT_FOUND_MESSAGE
        )
    return department


def _employee_company(
    session: Session, employee_id: uuid.UUID
) -> tuple[Employee, Department]:
    """Resolve the company from the employee's current department."""
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise DomainError(
            AttendanceErrorCode.INVALID_REFERENCE,
            EMPLOYEE_NOT_FOUND_MESSAGE,
            field_errors={"employee_id": EMPLOYEE_NOT_FOUND_MESSAGE},
        )
    return employee, _employee_department(session, employee)


def _employee_display(employee: Employee, department: Department) -> EmployeeDisplay:
    return EmployeeDisplay(
        employee_id=employee.id,
        employee_no=employee.employee_no,
        employee_name=employee.name,
        department_id=department.id,
        department_name=department.dept_name,
    )


def _company_employee_or_404(
    session: Session, company_id: uuid.UUID, employee_id: uuid.UUID
) -> tuple[Employee, Department]:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, EMPLOYEE_NOT_FOUND_MESSAGE)
    department = _employee_department(session, employee)
    if department.company_id != company_id:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, EMPLOYEE_NOT_FOUND_MESSAGE)
    return employee, department


def _company_department_or_404(
    session: Session, company_id: uuid.UUID, dept_id: uuid.UUID
) -> Department:
    department = session.get(Department, dept_id)
    if department is None or department.company_id != company_id:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, DEPARTMENT_NOT_FOUND_MESSAGE)
    return department


def _in_employment(employee: Employee, day: date) -> bool:
    if day < employee.hire_date:
        return False
    return employee.resign_date is None or day <= employee.resign_date


def _holiday_map(
    session: Session, company_id: uuid.UUID, month: date
) -> dict[date, HolidayDayType]:
    start, end = expansion.month_bounds(month)
    rows = session.exec(
        select(Holiday).where(
            col(Holiday.company_id) == company_id,
            col(Holiday.date) >= start,
            col(Holiday.date) <= end,
        )
    ).all()
    return {holiday.date: holiday.day_type for holiday in rows}


def _day_type(day: date, holidays: dict[date, HolidayDayType]) -> DayType:
    return resolve_day_type(day, holidays.get(day))


def _shift_public(shift: RosterEntryShift) -> RosterEntryShiftPublic:
    return RosterEntryShiftPublic(
        id=shift.id,
        seq=shift.seq,
        shift_id=shift.shift_id,
        shift_code=shift.shift_code,
        shift_name=shift.shift_name,
        start_time=shift.start_time,
        end_time=shift.end_time,
        cross_day=shift.cross_day,
        break_start=shift.break_start,
        break_end=shift.break_end,
        rest_minutes=shift.rest_minutes,
    )


def _shifts_by_entry(
    session: Session, entry_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[RosterEntryShift]]:
    result: dict[uuid.UUID, list[RosterEntryShift]] = defaultdict(list)
    if not entry_ids:
        return result
    for shift in session.exec(
        select(RosterEntryShift)
        .where(col(RosterEntryShift.roster_entry_id).in_(entry_ids))
        .order_by(col(RosterEntryShift.seq).asc())
    ).all():
        result[shift.roster_entry_id].append(shift)
    return result


def _entry_publics(
    session: Session, entries: list[RosterEntry]
) -> list[RosterEntryPublic]:
    if not entries:
        return []
    employee_ids = {entry.employee_id for entry in entries}
    employees = {
        employee.id: employee
        for employee in session.exec(
            select(Employee).where(col(Employee.id).in_(employee_ids))
        ).all()
    }
    departments = {
        department.id: department
        for department in session.exec(
            select(Department).where(
                col(Department.id).in_(
                    {employee.dept_id for employee in employees.values()}
                )
            )
        ).all()
    }
    shifts = _shifts_by_entry(session, [entry.id for entry in entries])
    result: list[RosterEntryPublic] = []
    for entry in entries:
        employee = employees.get(entry.employee_id)
        department = departments.get(employee.dept_id) if employee else None
        result.append(
            RosterEntryPublic(
                id=entry.id,
                company_id=entry.company_id,
                employee_id=entry.employee_id,
                employee_no=employee.employee_no if employee else None,
                employee_name=employee.name if employee else None,
                department_name=department.dept_name if department else None,
                work_date=entry.work_date,
                state=entry.state,
                source=entry.source,
                plan_id=entry.plan_id,
                note=entry.note,
                shifts=[_shift_public(shift) for shift in shifts.get(entry.id, [])],
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
        )
    return result


def _entry_public(session: Session, entry: RosterEntry) -> RosterEntryPublic:
    return _entry_publics(session, [entry])[0]


def _load_entries(
    session: Session,
    company_id: uuid.UUID,
    *,
    start: date | None = None,
    end: date | None = None,
    employee_id: uuid.UUID | None = None,
    dept_id: uuid.UUID | None = None,
    state: RosterState | None = None,
    source: RosterSource | None = None,
) -> list[RosterEntry]:
    filters: list[ColumnElement[bool]] = [col(RosterEntry.company_id) == company_id]
    statement = select(RosterEntry)
    if dept_id is not None:
        statement = statement.join(
            Employee, col(RosterEntry.employee_id) == col(Employee.id)
        )
        filters.append(col(Employee.dept_id) == dept_id)
    if start is not None:
        filters.append(col(RosterEntry.work_date) >= start)
    if end is not None:
        filters.append(col(RosterEntry.work_date) <= end)
    if employee_id is not None:
        filters.append(col(RosterEntry.employee_id) == employee_id)
    if state is not None:
        filters.append(col(RosterEntry.state) == state)
    if source is not None:
        filters.append(col(RosterEntry.source) == source)
    return list(
        session.exec(
            statement.where(*filters).order_by(
                col(RosterEntry.work_date).asc(),
                col(RosterEntry.employee_id).asc(),
            )
        ).all()
    )


# ---------------------------------------------------------------------------
# Reads: calendar, day, month, employee summaries
# ---------------------------------------------------------------------------


def read_employee_calendar(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str,
    employee_id: uuid.UUID,
) -> EmployeeRosterCalendarPublic:
    get_company_or_404(session, company_id)
    employee, department = _company_employee_or_404(session, company_id, employee_id)
    month_start = _month_string_start(month)
    start, end = expansion.month_bounds(month_start)
    holidays = _holiday_map(session, company_id, month_start)
    entries = {
        entry.work_date: entry
        for entry in _load_entries(
            session,
            company_id,
            start=start,
            end=end,
            employee_id=employee.id,
        )
    }
    shifts = _shifts_by_entry(session, [entry.id for entry in entries.values()])

    days: list[RosterCalendarDay] = []
    current = start
    while current <= end:
        entry = entries.get(current)
        if entry is None:
            days.append(
                RosterCalendarDay(
                    work_date=current,
                    day_type=_day_type(current, holidays),
                    state="unscheduled",
                )
            )
        else:
            days.append(
                RosterCalendarDay(
                    work_date=current,
                    day_type=_day_type(current, holidays),
                    state="work" if entry.state == RosterState.WORK else "rest",
                    source=entry.source,
                    plan_id=entry.plan_id,
                    shifts=[_shift_public(shift) for shift in shifts.get(entry.id, [])],
                    note=entry.note,
                )
            )
        current += timedelta(days=1)
    return EmployeeRosterCalendarPublic(
        employee=_employee_display(employee, department),
        month=month,
        days=days,
    )


def read_roster_day(
    session: Session,
    *,
    company_id: uuid.UUID,
    work_date: date,
    dept_id: uuid.UUID | None,
    plan_id: uuid.UUID | None,
    source: RosterSource | None,
) -> RosterDayPublic:
    get_company_or_404(session, company_id)
    if dept_id is not None:
        _company_department_or_404(session, company_id, dept_id)

    all_entries = _load_entries(
        session, company_id, start=work_date, end=work_date, dept_id=dept_id
    )
    scheduled_ids = {entry.employee_id for entry in all_entries}
    rows = [
        entry
        for entry in all_entries
        if (plan_id is None or entry.plan_id == plan_id)
        and (source is None or entry.source == source)
    ]

    employees = _company_employees(session, company_id, dept_id=dept_id)
    unscheduled_count = sum(
        1
        for employee in employees
        if employee.id not in scheduled_ids and _in_employment(employee, work_date)
    )

    departments = {
        department.id: department
        for department in session.exec(
            select(Department).where(
                col(Department.id).in_({e.dept_id for e in employees})
            )
        ).all()
    }
    employee_by_id = {employee.id: employee for employee in employees}
    shifts = _shifts_by_entry(session, [entry.id for entry in rows])
    day_employees: list[RosterDayEmployee] = []
    for entry in rows:
        entry_employee = employee_by_id.get(entry.employee_id)
        if entry_employee is None:
            # The employee transferred to another company after this row was
            # generated; the historical row stays but is not shown here.
            continue
        day_employees.append(
            RosterDayEmployee(
                employee=_employee_display(
                    entry_employee, departments[entry_employee.dept_id]
                ),
                state="work" if entry.state == RosterState.WORK else "rest",
                source=entry.source,
                plan_id=entry.plan_id,
                shifts=[_shift_public(shift) for shift in shifts.get(entry.id, [])],
                note=entry.note,
            )
        )
    return RosterDayPublic(
        date=work_date, employees=day_employees, unscheduled_count=unscheduled_count
    )


def _company_employees(
    session: Session, company_id: uuid.UUID, *, dept_id: uuid.UUID | None = None
) -> list[Employee]:
    employees = expansion.company_employees(session, company_id)
    if dept_id is None:
        return employees
    return [employee for employee in employees if employee.dept_id == dept_id]


def read_roster_month(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str,
    dept_id: uuid.UUID | None,
) -> RosterMonthPublic:
    get_company_or_404(session, company_id)
    if dept_id is not None:
        _company_department_or_404(session, company_id, dept_id)
    month_start = _month_string_start(month)
    start, end = expansion.month_bounds(month_start)
    holidays = _holiday_map(session, company_id, month_start)
    entries = _load_entries(
        session,
        company_id,
        start=start,
        end=end,
        dept_id=dept_id,
    )
    shifts = _shifts_by_entry(session, [entry.id for entry in entries])
    shift_colors = {
        shift.id: shift.color
        for shift in session.exec(
            select(Shift).where(
                col(Shift.id).in_(
                    {shift.shift_id for rows in shifts.values() for shift in rows}
                )
            )
        ).all()
    }

    employees = _company_employees(session, company_id, dept_id=dept_id)
    entries_by_date: dict[date, list[RosterEntry]] = defaultdict(list)
    for entry in entries:
        entries_by_date[entry.work_date].append(entry)
    scheduled_by_date = {
        day: {entry.employee_id for entry in rows}
        for day, rows in entries_by_date.items()
    }

    days: list[RosterMonthDayPublic] = []
    current = start
    while current <= end:
        day_entries = entries_by_date.get(current, [])
        counts: dict[uuid.UUID, ShiftCountAccumulator] = {}
        work_count = 0
        rest_count = 0
        manual_count = 0
        for entry in day_entries:
            if entry.source == RosterSource.MANUAL:
                manual_count += 1
            if entry.state == RosterState.REST:
                rest_count += 1
                continue
            work_count += 1
            for shift in shifts.get(entry.id, []):
                accumulator = counts.get(shift.shift_id)
                if accumulator is None:
                    counts[shift.shift_id] = ShiftCountAccumulator(shift=shift, count=1)
                else:
                    accumulator.count += 1
        scheduled = scheduled_by_date.get(current, set())
        unscheduled_count = sum(
            1
            for employee in employees
            if employee.id not in scheduled and _in_employment(employee, current)
        )
        days.append(
            RosterMonthDayPublic(
                date=current,
                day_type=_day_type(current, holidays),
                work_count=work_count,
                rest_count=rest_count,
                unscheduled_count=unscheduled_count,
                manual_count=manual_count,
                shift_counts=[
                    _shift_count_public(accumulator, shift_colors)
                    for accumulator in sorted(
                        counts.values(), key=lambda item: item.shift.shift_code
                    )
                ],
            )
        )
        current += timedelta(days=1)

    plans = session.exec(
        select(SchedulePlan)
        .where(
            col(SchedulePlan.company_id) == company_id,
            col(SchedulePlan.month) == month_start,
        )
        .order_by(col(SchedulePlan.plan_name).asc(), col(SchedulePlan.id).asc())
    ).all()
    return RosterMonthPublic(
        month=month,
        days=days,
        plans=[
            RosterMonthPlanPublic(
                id=plan.id,
                plan_name=plan.plan_name,
                scope_type=plan.scope_type,
                status=plan.status,
            )
            for plan in plans
        ],
    )


@dataclass
class ShiftCountAccumulator:
    shift: RosterEntryShift
    count: int


def _shift_count_public(
    accumulator: ShiftCountAccumulator, colors: dict[uuid.UUID, str | None]
) -> ShiftCountPublic:
    return ShiftCountPublic(
        shift_id=accumulator.shift.shift_id,
        shift_code=accumulator.shift.shift_code,
        shift_name=accumulator.shift.shift_name,
        color=colors.get(accumulator.shift.shift_id),
        count=accumulator.count,
    )


def read_roster_employees(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str,
    dept_id: uuid.UUID | None,
    keyword: str | None,
    skip: int,
    limit: int,
) -> RosterEmployeeSummariesPublic:
    get_company_or_404(session, company_id)
    if dept_id is not None:
        _company_department_or_404(session, company_id, dept_id)
    month_start = _month_string_start(month)
    start, end = expansion.month_bounds(month_start)

    filters: list[ColumnElement[bool]] = [
        col(Department.company_id) == company_id,
        col(Employee.hire_date) <= end,
        or_(col(Employee.resign_date).is_(None), col(Employee.resign_date) >= start),
    ]
    if dept_id is not None:
        filters.append(col(Employee.dept_id) == dept_id)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        filters.append(
            or_(
                col(Employee.employee_no).ilike(f"%{normalized_keyword}%"),
                col(Employee.name).ilike(f"%{normalized_keyword}%"),
            )
        )

    statement = (
        select(Employee)
        .join(Department, col(Employee.dept_id) == col(Department.id))
        .where(*filters)
        .order_by(col(Employee.employee_no).asc(), col(Employee.id).asc())
    )
    count_statement = (
        select(func.count())
        .select_from(Employee)
        .join(Department, col(Employee.dept_id) == col(Department.id))
        .where(*filters)
    )
    employees, count = paginate(
        session, statement, count_statement, skip=skip, limit=limit
    )
    employee_ids = [employee.id for employee in employees]

    entries_by_employee: dict[uuid.UUID, list[RosterEntry]] = defaultdict(list)
    if employee_ids:
        for entry in session.exec(
            select(RosterEntry).where(
                col(RosterEntry.company_id) == company_id,
                col(RosterEntry.employee_id).in_(employee_ids),
                col(RosterEntry.work_date) >= start,
                col(RosterEntry.work_date) <= end,
            )
        ).all():
            entries_by_employee[entry.employee_id].append(entry)

    department_ids = {employee.dept_id for employee in employees}
    departments = {
        department.id: department
        for department in session.exec(
            select(Department).where(col(Department.id).in_(department_ids))
        ).all()
    }

    data: list[RosterEmployeeSummaryPublic] = []
    for employee in employees:
        rows = entries_by_employee.get(employee.id, [])
        work_days = sum(1 for entry in rows if entry.state == RosterState.WORK)
        rest_days = sum(1 for entry in rows if entry.state == RosterState.REST)
        manual_exception_count = sum(
            1 for entry in rows if entry.source == RosterSource.MANUAL
        )
        employment_start = max(start, employee.hire_date)
        employment_end = (
            end if employee.resign_date is None else min(end, employee.resign_date)
        )
        employment_days = (employment_end - employment_start).days + 1
        unscheduled_days = max(0, employment_days - len(rows))
        department = departments[employee.dept_id]
        data.append(
            RosterEmployeeSummaryPublic(
                **_employee_display(employee, department).model_dump(),
                work_days=work_days,
                rest_days=rest_days,
                unscheduled_days=unscheduled_days,
                manual_exception_count=manual_exception_count,
            )
        )
    return RosterEmployeeSummariesPublic(data=data, count=count)


# ---------------------------------------------------------------------------
# Entry list and detail
# ---------------------------------------------------------------------------


def list_roster_entries(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str | None,
    employee_id: uuid.UUID | None,
    dept_id: uuid.UUID | None,
    state: RosterState | None,
    source: RosterSource | None,
    skip: int,
    limit: int,
) -> RosterEntriesPublic:
    get_company_or_404(session, company_id)
    if dept_id is not None:
        _company_department_or_404(session, company_id, dept_id)
    start: date | None = None
    end: date | None = None
    if month is not None:
        start, end = expansion.month_bounds(_month_string_start(month))

    filters: list[ColumnElement[bool]] = [col(RosterEntry.company_id) == company_id]
    statement = select(RosterEntry)
    count_statement = select(func.count()).select_from(RosterEntry)
    if dept_id is not None:
        statement = statement.join(
            Employee, col(RosterEntry.employee_id) == col(Employee.id)
        )
        count_statement = count_statement.join(
            Employee, col(RosterEntry.employee_id) == col(Employee.id)
        )
        filters.append(col(Employee.dept_id) == dept_id)
    if start is not None:
        filters.append(col(RosterEntry.work_date) >= start)
    if end is not None:
        filters.append(col(RosterEntry.work_date) <= end)
    if employee_id is not None:
        filters.append(col(RosterEntry.employee_id) == employee_id)
    if state is not None:
        filters.append(col(RosterEntry.state) == state)
    if source is not None:
        filters.append(col(RosterEntry.source) == source)

    statement = statement.where(*filters).order_by(
        col(RosterEntry.work_date).asc(),
        col(RosterEntry.employee_id).asc(),
        col(RosterEntry.id).asc(),
    )
    count_statement = count_statement.where(*filters)
    entries, count = paginate(
        session, statement, count_statement, skip=skip, limit=limit
    )
    return RosterEntriesPublic(
        data=_entry_publics(session, list(entries)),
        count=count,
    )


def get_roster_entry(session: Session, entry_id: uuid.UUID) -> RosterEntryPublic:
    entry = session.get(RosterEntry, entry_id)
    if entry is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, ROSTER_ENTRY_NOT_FOUND_MESSAGE)
    return _entry_public(session, entry)


# ---------------------------------------------------------------------------
# Manual exception validation and persistence
# ---------------------------------------------------------------------------


class _ShiftRow(Protocol):
    """Both request shift rows and stored snapshots satisfy this shape."""

    seq: int
    shift_id: uuid.UUID


@dataclass
class _ValidatedManualEntry:
    employee: Employee
    department: Department
    work_date: date
    state: RosterState
    shifts: list[tuple[int, Shift]]


def _field_error(
    code: AttendanceErrorCode, message: str, field: str, prefix: str
) -> DomainError:
    return DomainError(code, message, field_errors={f"{prefix}{field}": message})


def _validate_manual_entry(
    session: Session,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    work_date: date,
    state: RosterState,
    shift_inputs: Sequence[_ShiftRow],
    *,
    prefix: str,
    allow_inactive_shifts: bool = False,
) -> _ValidatedManualEntry:
    """Validate one manual exception; field keys stay batch-indexable."""
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise _field_error(
            AttendanceErrorCode.INVALID_REFERENCE,
            EMPLOYEE_NOT_FOUND_MESSAGE,
            "employee_id",
            prefix,
        )
    department = session.get(Department, employee.dept_id)
    if department is None or department.company_id != company_id:
        raise _field_error(
            AttendanceErrorCode.CROSS_COMPANY,
            CROSS_COMPANY_MESSAGE,
            "employee_id",
            prefix,
        )
    if not _in_employment(employee, work_date):
        raise _field_error(
            AttendanceErrorCode.EMPLOYEE_OUT_OF_RANGE,
            EMPLOYEE_OUT_OF_RANGE_MESSAGE,
            "work_date",
            prefix,
        )

    if state == RosterState.REST and shift_inputs:
        raise _field_error(
            AttendanceErrorCode.INVALID_SCOPE, STATE_SHIFTS_MESSAGE, "shifts", prefix
        )
    if state == RosterState.WORK and not shift_inputs:
        raise _field_error(
            AttendanceErrorCode.INVALID_SCOPE, STATE_SHIFTS_MESSAGE, "shifts", prefix
        )

    seen_seq: set[int] = set()
    seen_shift: set[uuid.UUID] = set()
    shifts: list[tuple[int, Shift]] = []
    for item in shift_inputs:
        if item.seq in seen_seq:
            raise _field_error(
                AttendanceErrorCode.INVALID_SCOPE,
                DUPLICATE_SEQ_MESSAGE,
                "shifts",
                prefix,
            )
        if item.shift_id in seen_shift:
            raise _field_error(
                AttendanceErrorCode.INVALID_SCOPE,
                DUPLICATE_SHIFT_MESSAGE,
                "shifts",
                prefix,
            )
        seen_seq.add(item.seq)
        seen_shift.add(item.shift_id)
        shift = session.get(Shift, item.shift_id)
        if shift is None:
            raise _field_error(
                AttendanceErrorCode.INVALID_REFERENCE,
                SHIFT_MISSING_MESSAGE,
                "shifts",
                prefix,
            )
        if shift.company_id != company_id:
            raise _field_error(
                AttendanceErrorCode.CROSS_COMPANY,
                CROSS_COMPANY_MESSAGE,
                "shifts",
                prefix,
            )
        if not shift.is_active and not allow_inactive_shifts:
            raise _field_error(
                AttendanceErrorCode.INACTIVE_REFERENCE,
                SHIFT_INACTIVE_MESSAGE,
                "shifts",
                prefix,
            )
        shifts.append((item.seq, shift))
    shifts.sort(key=lambda row: row[0])

    month_row = _existing_month(session, company_id, _month_start(work_date))
    if month_row is not None:
        if month_row.status == AttendanceMonthStatus.LOCKED:
            raise _field_error(
                AttendanceErrorCode.MONTH_LOCKED,
                MONTH_LOCKED_MESSAGE,
                "work_date",
                prefix,
            )
        if month_row.status == AttendanceMonthStatus.CONFIRMED:
            raise _field_error(
                AttendanceErrorCode.MONTH_CONFIRMED,
                MONTH_CONFIRMED_MESSAGE,
                "work_date",
                prefix,
            )
    return _ValidatedManualEntry(
        employee=employee,
        department=department,
        work_date=work_date,
        state=state,
        shifts=shifts,
    )


def _shift_snapshot_rows(
    entry_id: uuid.UUID, shifts: list[tuple[int, Shift]]
) -> list[RosterEntryShift]:
    return [
        RosterEntryShift(
            roster_entry_id=entry_id,
            seq=seq,
            shift_id=shift.id,
            shift_code=shift.shift_code,
            shift_name=shift.shift_name,
            start_time=shift.start_time,
            end_time=shift.end_time,
            cross_day=shift.cross_day,
            break_start=shift.break_start,
            break_end=shift.break_end,
            rest_minutes=shift.rest_minutes,
        )
        for seq, shift in shifts
    ]


def _replace_shifts(
    session: Session, entry: RosterEntry, shifts: list[tuple[int, Shift]]
) -> None:
    session.exec(
        delete(RosterEntryShift).where(
            col(RosterEntryShift.roster_entry_id) == entry.id
        )
    )
    for row in _shift_snapshot_rows(entry.id, shifts):
        session.add(row)


def _winner_plan_id(
    session: Session,
    candidates_cache: dict[date, list[expansion.PlanCandidate]],
    company_id: uuid.UUID,
    employee: Employee,
    work_date: date,
) -> uuid.UUID | None:
    month = _month_start(work_date)
    candidates = candidates_cache.get(month)
    if candidates is None:
        candidates = expansion.load_candidates(session, company_id, month)
        candidates_cache[month] = candidates
    try:
        winner = expansion.resolve_winner(candidates, employee)
    except expansion.SamePrecisionConflict:
        raise DomainError(AttendanceErrorCode.SCHEDULE_CONFLICT, SAME_PRECISION_MESSAGE)
    return winner.plan_id if winner is not None else None


def _remove_entry_and_shifts(session: Session, entry: RosterEntry) -> None:
    session.exec(
        delete(RosterEntryShift).where(
            col(RosterEntryShift.roster_entry_id) == entry.id
        )
    )
    session.delete(entry)
    session.flush()


def _restore_plan_entry(
    session: Session,
    candidates_cache: dict[date, list[expansion.PlanCandidate]],
    *,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    work_date: date,
) -> None:
    """Re-resolve one employee-day against current enabled plans."""
    employee = session.get(Employee, employee_id)
    if employee is None or not _in_employment(employee, work_date):
        return
    month = _month_start(work_date)
    candidates = candidates_cache.get(month)
    if candidates is None:
        candidates = expansion.load_candidates(session, company_id, month)
        candidates_cache[month] = candidates
    try:
        winner = expansion.resolve_winner(candidates, employee)
    except expansion.SamePrecisionConflict:
        raise DomainError(AttendanceErrorCode.SCHEDULE_CONFLICT, SAME_PRECISION_MESSAGE)
    if winner is None:
        return
    shifts = winner.shifts_by_day.get(work_date.day, ())
    entry = RosterEntry(
        company_id=company_id,
        employee_id=employee_id,
        work_date=work_date,
        state=RosterState.WORK if shifts else RosterState.REST,
        source=RosterSource.PLAN,
        plan_id=winner.plan_id,
    )
    session.add(entry)
    session.flush()
    for row in _shift_snapshot_rows(entry.id, list(enumerate(shifts))):
        session.add(row)
    session.flush()


def _apply_manual_entry(
    session: Session,
    validated: _ValidatedManualEntry,
    candidates_cache: dict[date, list[expansion.PlanCandidate]],
    *,
    existing: RosterEntry | None,
    note: str | None,
) -> tuple[RosterEntry, Literal["created", "updated"]]:
    now = get_datetime_utc()
    if existing is None:
        plan_id = _winner_plan_id(
            session,
            candidates_cache,
            validated.department.company_id,
            validated.employee,
            validated.work_date,
        )
        entry = RosterEntry(
            company_id=validated.department.company_id,
            employee_id=validated.employee.id,
            work_date=validated.work_date,
            state=validated.state,
            source=RosterSource.MANUAL,
            plan_id=plan_id,
            note=note,
        )
        session.add(entry)
        session.flush()
        outcome: Literal["created", "updated"] = "created"
    else:
        entry = existing
        if entry.source == RosterSource.MANUAL:
            plan_id = entry.plan_id
        else:
            plan_id = entry.plan_id or _winner_plan_id(
                session,
                candidates_cache,
                validated.department.company_id,
                validated.employee,
                validated.work_date,
            )
        entry.state = validated.state
        entry.source = RosterSource.MANUAL
        entry.plan_id = plan_id
        entry.note = note
        entry.updated_at = now
        session.add(entry)
        outcome = "updated"
    _replace_shifts(session, entry, validated.shifts)
    session.flush()
    return entry, outcome


def _entry_by_employee_date(
    session: Session, employee_id: uuid.UUID, work_date: date
) -> RosterEntry | None:
    return session.exec(
        select(RosterEntry).where(
            col(RosterEntry.employee_id) == employee_id,
            col(RosterEntry.work_date) == work_date,
        )
    ).first()


# ---------------------------------------------------------------------------
# Manual exception CRUD
# ---------------------------------------------------------------------------


def create_roster_entry(
    session: Session, payload: RosterEntryCreate
) -> RosterEntryPublic:
    employee, department = _employee_company(session, payload.employee_id)
    company_id = department.company_id
    month_row = _get_or_create_month(
        session, company_id, _month_start(payload.work_date)
    )
    _ensure_month_editable(month_row)
    validated = _validate_manual_entry(
        session,
        company_id,
        payload.employee_id,
        payload.work_date,
        payload.state,
        payload.shifts,
        prefix="",
    )
    candidates_cache: dict[date, list[expansion.PlanCandidate]] = {}
    existing = _entry_by_employee_date(
        session, validated.employee.id, validated.work_date
    )
    entry, _ = _apply_manual_entry(
        session,
        validated,
        candidates_cache,
        existing=existing,
        note=payload.note,
    )
    mark_month_stale(month_row)
    session.commit()
    session.refresh(entry)
    return _entry_public(session, entry)


def update_roster_entry(
    session: Session, entry_id: uuid.UUID, payload: RosterEntryUpdate
) -> RosterEntryPublic:
    entry = session.get(RosterEntry, entry_id)
    if entry is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, ROSTER_ENTRY_NOT_FOUND_MESSAGE)
    if entry.source != RosterSource.MANUAL:
        raise DomainError(
            AttendanceErrorCode.ROSTER_ENTRY_NOT_MANUAL, NOT_MANUAL_MESSAGE
        )
    month_row = _get_or_create_month(
        session, entry.company_id, _month_start(entry.work_date)
    )
    _ensure_month_editable(month_row)

    fields = payload.model_fields_set
    state = payload.state if "state" in fields else entry.state
    if state is None:
        raise AssertionError("state is non-nullable")
    shift_inputs: list[_ShiftRow]
    shifts_unchanged = "shifts" not in fields
    if "shifts" in fields:
        shift_inputs = list(payload.shifts or [])
    elif state == RosterState.REST:
        shift_inputs = []
    else:
        shift_inputs = [
            _ShiftInput(seq=shift.seq, shift_id=shift.shift_id)
            for shift in session.exec(
                select(RosterEntryShift)
                .where(col(RosterEntryShift.roster_entry_id) == entry.id)
                .order_by(col(RosterEntryShift.seq).asc())
            ).all()
        ]
    validated = _validate_manual_entry(
        session,
        entry.company_id,
        entry.employee_id,
        entry.work_date,
        state,
        shift_inputs,
        prefix="",
        allow_inactive_shifts=shifts_unchanged,
    )
    note = payload.note if "note" in fields else entry.note
    entry.state = validated.state
    entry.note = note
    entry.updated_at = get_datetime_utc()
    session.add(entry)
    _replace_shifts(session, entry, validated.shifts)
    mark_month_stale(month_row)
    session.commit()
    session.refresh(entry)
    return _entry_public(session, entry)


@dataclass
class _ShiftInput:
    """Adapter so stored snapshots validate like request shift rows."""

    seq: int
    shift_id: uuid.UUID


def delete_roster_entry(session: Session, entry_id: uuid.UUID) -> Message:
    entry = session.get(RosterEntry, entry_id)
    if entry is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, ROSTER_ENTRY_NOT_FOUND_MESSAGE)
    if entry.source != RosterSource.MANUAL:
        raise DomainError(
            AttendanceErrorCode.ROSTER_ENTRY_NOT_MANUAL, NOT_MANUAL_MESSAGE
        )
    month_row = _get_or_create_month(
        session, entry.company_id, _month_start(entry.work_date)
    )
    _ensure_month_editable(month_row)
    candidates_cache: dict[date, list[expansion.PlanCandidate]] = {}
    company_id = entry.company_id
    employee_id = entry.employee_id
    work_date = entry.work_date
    _remove_entry_and_shifts(session, entry)
    _restore_plan_entry(
        session,
        candidates_cache,
        company_id=company_id,
        employee_id=employee_id,
        work_date=work_date,
    )
    mark_month_stale(month_row)
    session.commit()
    return Message(message="人工例外删除成功")


# ---------------------------------------------------------------------------
# Batch exceptions
# ---------------------------------------------------------------------------


def batch_entries(
    session: Session, payload: RosterEntryBatchRequest
) -> RosterEntryBatchResult:
    get_company_or_404(session, payload.company_id)
    field_errors: dict[str, str] = {}
    validated: list[tuple[int, RosterEntryUpsert, _ValidatedManualEntry]] = []
    seen_keys: dict[tuple[uuid.UUID, date], int] = {}

    for index, item in enumerate(payload.entries):
        prefix = f"entries[{index}]."
        try:
            entry = _validate_manual_entry(
                session,
                payload.company_id,
                item.employee_id,
                item.work_date,
                item.state,
                item.shifts,
                prefix=prefix,
            )
        except DomainError as error:
            field_errors.update(
                error.field_errors or {f"{prefix}work_date": error.message}
            )
            continue
        key = (entry.employee.id, entry.work_date)
        if key in seen_keys:
            field_errors[f"{prefix}work_date"] = DUPLICATE_DAY_MESSAGE
            continue
        seen_keys[key] = index
        if item.entry_id is not None:
            existing = session.get(RosterEntry, item.entry_id)
            if existing is None or existing.company_id != payload.company_id:
                field_errors[f"{prefix}entry_id"] = ROSTER_ENTRY_NOT_FOUND_MESSAGE
                continue
            if existing.source != RosterSource.MANUAL:
                field_errors[f"{prefix}entry_id"] = NOT_MANUAL_MESSAGE
                continue
            if (
                existing.employee_id != entry.employee.id
                or existing.work_date != entry.work_date
            ):
                field_errors[f"{prefix}employee_id"] = "明细的员工或日期不一致"
                continue
        validated.append((index, item, entry))

    deleted: list[RosterEntry] = []
    seen_delete_ids: set[uuid.UUID] = set()
    for index, delete_id in enumerate(payload.delete_entry_ids):
        prefix = f"delete_entry_ids[{index}]"
        if delete_id in seen_delete_ids:
            field_errors[prefix] = DELETE_DUPLICATE_MESSAGE
            continue
        seen_delete_ids.add(delete_id)
        existing = session.get(RosterEntry, delete_id)
        if existing is None or existing.company_id != payload.company_id:
            field_errors[prefix] = DELETE_NOT_FOUND_MESSAGE
            continue
        if existing.source != RosterSource.MANUAL:
            field_errors[prefix] = DELETE_NOT_MANUAL_MESSAGE
            continue
        key = (existing.employee_id, existing.work_date)
        if key in seen_keys:
            field_errors[f"entries[{seen_keys[key]}].work_date"] = (
                "同一条排班明细不能同时更新和删除"
            )
            continue
        month_row = _existing_month(
            session, existing.company_id, _month_start(existing.work_date)
        )
        if month_row is not None and month_row.status not in EDITABLE_MONTH_STATUSES:
            field_errors[prefix] = (
                MONTH_LOCKED_MESSAGE
                if month_row.status == AttendanceMonthStatus.LOCKED
                else MONTH_CONFIRMED_MESSAGE
            )
            continue
        deleted.append(existing)

    if field_errors:
        raise DomainError(
            AttendanceErrorCode.ROSTER_BATCH_INVALID,
            BATCH_INVALID_MESSAGE,
            field_errors=field_errors,
        )

    candidates_cache: dict[date, list[expansion.PlanCandidate]] = {}
    months: dict[date, AttendanceMonth] = {}
    created = updated = 0
    for _index, item, entry in validated:
        month_row = months.get(_month_start(entry.work_date))
        if month_row is None:
            month_row = _get_or_create_month(
                session, payload.company_id, _month_start(entry.work_date)
            )
            months[_month_start(entry.work_date)] = month_row
        existing = (
            session.get(RosterEntry, item.entry_id)
            if item.entry_id is not None
            else _entry_by_employee_date(session, entry.employee.id, entry.work_date)
        )
        _, outcome = _apply_manual_entry(
            session,
            entry,
            candidates_cache,
            existing=existing,
            note=item.note,
        )
        if outcome == "created":
            created += 1
        else:
            updated += 1

    for existing in deleted:
        month_row = months.get(_month_start(existing.work_date))
        if month_row is None:
            month_row = _get_or_create_month(
                session, payload.company_id, _month_start(existing.work_date)
            )
            months[_month_start(existing.work_date)] = month_row
        company_id = existing.company_id
        employee_id = existing.employee_id
        work_date = existing.work_date
        _remove_entry_and_shifts(session, existing)
        _restore_plan_entry(
            session,
            candidates_cache,
            company_id=company_id,
            employee_id=employee_id,
            work_date=work_date,
        )

    for month_row in months.values():
        _ensure_month_editable(month_row)
        mark_month_stale(month_row)
    session.commit()
    return RosterEntryBatchResult(
        created=created,
        updated=updated,
        deleted=len(deleted),
        month_stale=any(month.is_stale for month in months.values()),
    )


# ---------------------------------------------------------------------------
# Personnel sync
# ---------------------------------------------------------------------------


def _sync_preview(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    reconciliation: expansion.Reconciliation,
    change: expansion.RosterChange,
) -> PersonnelSyncPreview:
    start, end = expansion.month_bounds(month)
    existing_entries = session.exec(
        select(RosterEntry).where(
            col(RosterEntry.company_id) == company_id,
            col(RosterEntry.work_date) >= start,
            col(RosterEntry.work_date) <= end,
        )
    ).all()
    existing_ids = {entry.employee_id for entry in existing_entries}
    deleted_entry_ids = {entry.id for entry in reconciliation.deleted}
    added_ids = {entry.employee_id for entry in reconciliation.added}
    updated_ids = {update.entry.employee_id for update in reconciliation.updated}
    deleted_ids = {entry.employee_id for entry in reconciliation.deleted}
    # Any surviving row (plan or manual) keeps the employee in scope, so a
    # partial month (e.g. a mid-month resignation) counts as changed, not
    # removed.
    desired_ids = {
        entry.employee_id
        for entry in existing_entries
        if entry.id not in deleted_entry_ids
    } | added_ids

    added_set = added_ids - existing_ids
    removed_set = {
        employee_id for employee_id in deleted_ids if employee_id not in desired_ids
    }
    changed_set = (added_ids | updated_ids | deleted_ids) - added_set - removed_set
    return PersonnelSyncPreview(
        added=len(added_set),
        removed=len(removed_set),
        changed=len(changed_set),
        entries_added=change.added,
        entries_updated=change.updated,
        entries_deleted=change.deleted,
        manual_preserved=change.manual_preserved,
    )


def _sync_reconciliation(
    session: Session, company_id: uuid.UUID, month: date
) -> tuple[expansion.Reconciliation, expansion.RosterChange, PersonnelSyncPreview]:
    candidates = expansion.load_candidates(session, company_id, month)
    try:
        reconciliation = expansion.plan_expansion(
            session, company_id, month, candidates
        )
    except expansion.SamePrecisionConflict:
        raise DomainError(AttendanceErrorCode.SCHEDULE_CONFLICT, SAME_PRECISION_MESSAGE)
    change = reconciliation.change()
    preview = _sync_preview(session, company_id, month, reconciliation, change)
    return reconciliation, change, preview


def sync_preview(
    session: Session, *, company_id: uuid.UUID, month: str
) -> PersonnelSyncPreview:
    get_company_or_404(session, company_id)
    month_start = _month_string_start(month)
    month_row = _existing_month(session, company_id, month_start)
    if month_row is not None:
        _ensure_month_expandable(month_row, SYNC_BLOCKED_MESSAGE)
    _, _, preview = _sync_reconciliation(session, company_id, month_start)
    return preview


def sync_personnel(
    session: Session, payload: PersonnelSyncRequest
) -> PersonnelSyncResult:
    get_company_or_404(session, payload.company_id)
    month_start = _month_string_start(payload.month)
    month_row = _get_or_create_month(session, payload.company_id, month_start)
    _ensure_month_expandable(month_row, SYNC_BLOCKED_MESSAGE)
    reconciliation, _change, preview = _sync_reconciliation(
        session, payload.company_id, month_start
    )
    expansion.apply_plan(reconciliation, session, payload.company_id)
    mark_month_stale(month_row)
    session.commit()
    return PersonnelSyncResult(
        **preview.model_dump(),
        month_stale=month_row.is_stale,
    )
