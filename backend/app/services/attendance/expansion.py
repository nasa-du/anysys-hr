"""Monthly roster expansion for schedule plans (spec section 5.1).

Expansion is a company + month-level full re-expansion. It resolves the
highest-specificity plan for every employee-day, then reconciles plan-generated
``roster_entry`` rows to match. Manual exceptions are never modified.

The functions here never commit: plan save, archive/unarchive, explicit
expand, copy, and (in a later slice) personnel sync call them inside their own
transaction so the plan definition, the roster rows, and the stale flag land
together.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, time, timedelta

from sqlalchemy import delete
from sqlmodel import Session, col, select

from app.enums import PlanStatus, RosterSource, RosterState, ScheduleScopeType
from app.models import (
    Department,
    Employee,
    PlanDay,
    PlanScope,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
    get_datetime_utc,
)

# Lower rank wins: employee > position > dept > all.
SCOPE_PRIORITY: dict[ScheduleScopeType, int] = {
    ScheduleScopeType.EMPLOYEE: 0,
    ScheduleScopeType.POSITION: 1,
    ScheduleScopeType.DEPT: 2,
    ScheduleScopeType.ALL: 3,
}

SECONDS_PER_DAY = 24 * 60 * 60


@dataclass(frozen=True)
class PlanCandidate:
    """An enabled plan's in-memory shape for one month."""

    plan_id: uuid.UUID
    plan_name: str
    scope_type: ScheduleScopeType
    scope_ids: frozenset[uuid.UUID]
    shifts_by_day: dict[int, tuple[Shift, ...]] = field(default_factory=dict)


@dataclass
class RosterChange:
    """Counts shared by plan previews and mutation responses."""

    added: int = 0
    updated: int = 0
    deleted: int = 0
    manual_preserved: int = 0
    affected_employee_ids: set[uuid.UUID] = field(default_factory=set)


@dataclass(frozen=True)
class DesiredEntry:
    employee_id: uuid.UUID
    work_date: date
    state: RosterState
    plan_id: uuid.UUID
    shifts: tuple[Shift, ...]


@dataclass
class EntryUpdate:
    entry: RosterEntry
    desired: DesiredEntry


@dataclass
class Reconciliation:
    """The exact roster operations one expansion would perform."""

    added: list[DesiredEntry] = field(default_factory=list)
    updated: list[EntryUpdate] = field(default_factory=list)
    deleted: list[RosterEntry] = field(default_factory=list)
    manual_preserved: int = 0

    def change(self) -> RosterChange:
        affected = {entry.employee_id for entry in self.added}
        affected.update(update.entry.employee_id for update in self.updated)
        affected.update(entry.employee_id for entry in self.deleted)
        return RosterChange(
            added=len(self.added),
            updated=len(self.updated),
            deleted=len(self.deleted),
            manual_preserved=self.manual_preserved,
            affected_employee_ids=affected,
        )


def month_bounds(month: date) -> tuple[date, date]:
    """Return the first and last calendar day of a stored first-of-month date."""
    if month.month == 12:
        next_month = date(month.year + 1, 1, 1)
    else:
        next_month = date(month.year, month.month + 1, 1)
    return month, next_month - timedelta(days=1)


def days_in_month(month: date) -> int:
    start, end = month_bounds(month)
    return (end - start).days + 1


def candidate_matches(candidate: PlanCandidate, employee: Employee) -> bool:
    """Whether a plan covers the employee, regardless of the day's shifts.

    A plan that matches but has no shifts for the day wins as a rest day and
    suppresses lower-specificity plans. That is why matching is separate from
    the day's shift lookup.
    """
    if candidate.scope_type == ScheduleScopeType.ALL:
        return True
    if candidate.scope_type == ScheduleScopeType.EMPLOYEE:
        return employee.id in candidate.scope_ids
    if candidate.scope_type == ScheduleScopeType.POSITION:
        return employee.position_id in candidate.scope_ids
    return employee.dept_id in candidate.scope_ids


def resolve_winner(
    candidates: list[PlanCandidate], employee: Employee
) -> PlanCandidate | None:
    """Resolve one employee-day; a same-precision tie is a data error.

    Same-precision scope uniqueness is enforced on save, so a tie means the
    data was modified outside the service. The plan service turns the ``None``
    ambiguity into 409 ``schedule_conflict`` by checking this return shape.
    """
    matches = [
        candidate
        for candidate in candidates
        if candidate_matches(candidate, employee)
    ]
    if not matches:
        return None
    best_priority = min(SCOPE_PRIORITY[candidate.scope_type] for candidate in matches)
    winners = [
        candidate
        for candidate in matches
        if SCOPE_PRIORITY[candidate.scope_type] == best_priority
    ]
    if len(winners) > 1:
        raise SamePrecisionConflict(winners)
    return winners[0]


class SamePrecisionConflict(Exception):
    """Raised when two enabled plans cover one employee-day at the same level."""

    def __init__(self, candidates: list[PlanCandidate]) -> None:
        super().__init__("same-precision plan conflict")
        self.candidates = candidates


def company_employees(session: Session, company_id: uuid.UUID) -> list[Employee]:
    """Employees of one company ordered by employee number."""
    return list(
        session.exec(
            select(Employee)
            .join(Department, col(Employee.dept_id) == col(Department.id))
            .where(col(Department.company_id) == company_id)
            .order_by(col(Employee.employee_no).asc(), col(Employee.id).asc())
        ).all()
    )


def load_candidates(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    *,
    excluded_plan_ids: set[uuid.UUID] | None = None,
) -> list[PlanCandidate]:
    """Load enabled plans with their scopes and day shifts for one month."""
    plans = session.exec(
        select(SchedulePlan).where(
            col(SchedulePlan.company_id) == company_id,
            col(SchedulePlan.month) == month,
            col(SchedulePlan.status) == PlanStatus.ENABLED,
        )
    ).all()
    plans = [
        plan
        for plan in plans
        if excluded_plan_ids is None or plan.id not in excluded_plan_ids
    ]
    if not plans:
        return []

    plan_ids = [plan.id for plan in plans]
    scopes_by_plan: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for scope in session.exec(
        select(PlanScope).where(col(PlanScope.plan_id).in_(plan_ids))
    ).all():
        scopes_by_plan[scope.plan_id].add(scope.scope_id)

    days_by_plan: dict[uuid.UUID, dict[int, list[tuple[int, Shift]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for day_row, shift in session.exec(
        select(PlanDay, Shift)
        .join(Shift, col(PlanDay.shift_id) == col(Shift.id))
        .where(col(PlanDay.plan_id).in_(plan_ids))
        .order_by(col(PlanDay.day_of_month).asc(), col(PlanDay.seq).asc())
    ).all():
        days_by_plan[day_row.plan_id][day_row.day_of_month].append(
            (day_row.seq, shift)
        )

    candidates: list[PlanCandidate] = []
    for plan in plans:
        ordered_days = {
            day: tuple(shift for _, shift in sorted(rows, key=lambda row: row[0]))
            for day, rows in days_by_plan.get(plan.id, {}).items()
        }
        candidates.append(
            PlanCandidate(
                plan_id=plan.id,
                plan_name=plan.plan_name,
                scope_type=plan.scope_type,
                scope_ids=frozenset(scopes_by_plan.get(plan.id, set())),
                shifts_by_day=ordered_days,
            )
        )
    return candidates


def _snapshot_values(
    *,
    seq: int,
    shift_id: uuid.UUID,
    shift_code: str,
    shift_name: str,
    start_time: object,
    end_time: object,
    cross_day: bool,
    break_start: object,
    break_end: object,
    rest_minutes: int,
) -> tuple[object, ...]:
    return (
        seq,
        shift_id,
        shift_code,
        shift_name,
        start_time,
        end_time,
        cross_day,
        break_start,
        break_end,
        rest_minutes,
    )


def _snapshot_key(shift: RosterEntryShift) -> tuple[object, ...]:
    return _snapshot_values(
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


def _desired_snapshot_key(seq: int, shift: Shift) -> tuple[object, ...]:
    return _snapshot_values(
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


def _load_entries(
    session: Session, company_id: uuid.UUID, month: date
) -> tuple[dict[tuple[uuid.UUID, date], RosterEntry], dict[uuid.UUID, list[RosterEntryShift]]]:
    start, end = month_bounds(month)
    entries = session.exec(
        select(RosterEntry).where(
            col(RosterEntry.company_id) == company_id,
            col(RosterEntry.work_date) >= start,
            col(RosterEntry.work_date) <= end,
        )
    ).all()
    by_key = {(entry.employee_id, entry.work_date): entry for entry in entries}
    shifts_by_entry: dict[uuid.UUID, list[RosterEntryShift]] = defaultdict(list)
    if entries:
        for shift in session.exec(
            select(RosterEntryShift)
            .where(col(RosterEntryShift.roster_entry_id).in_([e.id for e in entries]))
            .order_by(col(RosterEntryShift.seq).asc())
        ).all():
            shifts_by_entry[shift.roster_entry_id].append(shift)
    return by_key, shifts_by_entry


def _desired_entries(
    employees: list[Employee],
    candidates: list[PlanCandidate],
    month: date,
) -> dict[tuple[uuid.UUID, date], DesiredEntry]:
    start, end = month_bounds(month)
    desired: dict[tuple[uuid.UUID, date], DesiredEntry] = {}
    for employee in employees:
        current = start
        while current <= end:
            if current < employee.hire_date or (
                employee.resign_date is not None and current > employee.resign_date
            ):
                current += timedelta(days=1)
                continue
            winner = resolve_winner(candidates, employee)
            if winner is not None:
                shifts = winner.shifts_by_day.get(current.day, ())
                desired[(employee.id, current)] = DesiredEntry(
                    employee_id=employee.id,
                    work_date=current,
                    state=RosterState.WORK if shifts else RosterState.REST,
                    plan_id=winner.plan_id,
                    shifts=shifts,
                )
            current += timedelta(days=1)
    return desired


def plan_expansion(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    candidates: list[PlanCandidate],
    *,
    employees: list[Employee] | None = None,
    reserved_keys: set[tuple[uuid.UUID, date]] | None = None,
) -> Reconciliation:
    """Compute (but do not apply) the roster reconciliation for one month.

    ``reserved_keys`` are employee-days that will be covered by manual entries
    (used by copy previews before the copied exceptions exist). They suppress
    plan entries exactly like persisted manual rows.
    """
    reserved = reserved_keys or set()
    desired = _desired_entries(
        employees if employees is not None else company_employees(session, company_id),
        candidates,
        month,
    )
    existing, shifts_by_entry = _load_entries(session, company_id, month)
    plan = Reconciliation()
    for key in reserved:
        desired.pop(key, None)
        if key not in existing:
            plan.manual_preserved += 1

    for (employee_id, work_date), entry in existing.items():
        if entry.source == RosterSource.MANUAL:
            # Manual exceptions always win; also drop the desired key so the
            # plan never tries to add a second row for the same employee-day.
            desired.pop((employee_id, work_date), None)
            plan.manual_preserved += 1
            continue
        target = desired.pop((employee_id, work_date), None)
        if target is None:
            plan.deleted.append(entry)
            continue
        desired_keys = [
            _desired_snapshot_key(seq, shift)
            for seq, shift in enumerate(target.shifts)
        ]
        existing_keys = [_snapshot_key(shift) for shift in shifts_by_entry.get(entry.id, [])]
        if (
            entry.state == target.state
            and entry.plan_id == target.plan_id
            and existing_keys == desired_keys
        ):
            continue
        plan.updated.append(EntryUpdate(entry=entry, desired=target))

    for target in desired.values():
        plan.added.append(target)
    return plan


def _apply_shift_snapshots(
    session: Session, entry: RosterEntry, shifts: tuple[Shift, ...]
) -> None:
    session.execute(
        delete(RosterEntryShift).where(
            col(RosterEntryShift.roster_entry_id) == entry.id
        )
    )
    for seq, shift in enumerate(shifts):
        session.add(
            RosterEntryShift(
                roster_entry_id=entry.id,
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
        )


def apply_plan(
    plan: Reconciliation, session: Session, company_id: uuid.UUID
) -> RosterChange:
    """Apply a computed reconciliation; the caller owns the transaction."""
    now = get_datetime_utc()
    for entry in plan.deleted:
        session.delete(entry)
    for target in plan.added:
        entry = RosterEntry(
            company_id=company_id,
            employee_id=target.employee_id,
            work_date=target.work_date,
            state=target.state,
            source=RosterSource.PLAN,
            plan_id=target.plan_id,
        )
        session.add(entry)
        session.flush()
        if target.shifts:
            _apply_shift_snapshots(session, entry, target.shifts)
    for update in plan.updated:
        entry = update.entry
        entry.state = update.desired.state
        entry.plan_id = update.desired.plan_id
        entry.updated_at = now
        session.add(entry)
        _apply_shift_snapshots(session, entry, update.desired.shifts)
    session.flush()
    return plan.change()


def expand_month(
    session: Session,
    company_id: uuid.UUID,
    month: date,
) -> RosterChange:
    """Full re-expansion for one company-month inside the caller's transaction."""
    candidates = load_candidates(session, company_id, month)
    plan = plan_expansion(session, company_id, month, candidates)
    return apply_plan(plan, session, company_id)


def shift_overlap_warnings(
    shift_rows: list[tuple[int, Shift]],
) -> list[str]:
    """Warn about overlapping same-day shifts and a cross-day shift meeting the next day.

    These are warnings only: the spec keeps saving unblocked for them.
    """
    warnings: list[str] = []
    by_day: dict[int, list[Shift]] = defaultdict(list)
    for day, shift in shift_rows:
        by_day[day].append(shift)

    for day in sorted(by_day):
        same_day = by_day[day]
        for index, first in enumerate(same_day):
            for second in same_day[index + 1 :]:
                if _overlaps_same_day(first, second):
                    warnings.append(
                        f"第 {day} 天的「{first.shift_name}」与「{second.shift_name}」时间重叠"
                    )
        next_day = by_day.get(day + 1, [])
        for first in same_day:
            if not first.cross_day:
                continue
            for second in next_day:
                if _cross_day_meets_next(first, second):
                    warnings.append(
                        f"第 {day} 天的跨天「{first.shift_name}」与第 {day + 1} 天的"
                        f"「{second.shift_name}」时间重叠"
                    )
    return warnings


def _seconds(value: time) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def _overlaps_same_day(first: Shift, second: Shift) -> bool:
    first_start = _seconds(first.start_time)
    first_end = first_start + _shift_span(first)
    second_start = _seconds(second.start_time)
    second_end = second_start + _shift_span(second)
    return first_start < second_end and second_start < first_end


def _shift_span(shift: Shift) -> int:
    span = (_seconds(shift.end_time) - _seconds(shift.start_time)) % SECONDS_PER_DAY
    if span == 0:
        span = SECONDS_PER_DAY
    return span


def _cross_day_meets_next(first: Shift, second: Shift) -> bool:
    first_start = _seconds(first.start_time)
    first_end = first_start + _shift_span(first)
    second_start = SECONDS_PER_DAY + _seconds(second.start_time)
    second_end = second_start + _shift_span(second)
    return first_start < second_end and second_start < first_end
