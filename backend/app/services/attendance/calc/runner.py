"""Month orchestration, summaries, and the public ``run_month`` seam."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from fractions import Fraction

from app.enums import (
    DayStatus,
    DayType,
    HolidayDayType,
    ResultRosterState,
    RosterState,
)
from app.services.attendance.calc._common import (
    amount_value,
    dates_in,
    day_value,
    ensure_aware,
    hours_value,
    month_bounds,
)
from app.services.attendance.calc.days import (
    DayComputation,
    DayContext,
    calculate_day,
)
from app.services.attendance.calc.leave import LeaveAllocation, allocate_leave
from app.services.attendance.calc.models import (
    CALC_VERSION,
    DayResult,
    Employee,
    MonthInputs,
    MonthOutputs,
    MonthSummary,
    Punch,
    Rules,
    RunSummary,
    ShiftSnapshot,
    Trip,
)
from app.services.attendance.calc.punching import (
    ShiftInstance,
    build_shift_instances,
)

_NO_DATA_REASON = "no_data"
_OUT_OF_EMPLOYMENT_REASON = "out_of_employment"


@dataclass(frozen=True, slots=True)
class RosterEntryView:
    state: ResultRosterState
    shifts: tuple[ShiftSnapshot, ...]
    rules: Rules | None = None


@dataclass(frozen=True, slots=True)
class _EmployeeIndex:
    """One employee's month index, built once for scope, keys, and days."""

    employee_id: str
    roster: Mapping[date, RosterEntryView]
    instances: Mapping[date, tuple[ShiftInstance, ...]]
    punches: Mapping[date, tuple[Punch, ...]]
    trips: tuple[Trip, ...]
    overtime: Mapping[date, int]
    leave: LeaveAllocation
    data_dates: frozenset[date]


def _index_inputs(
    inputs: MonthInputs, month_start: date, month_end: date
) -> dict[str, _EmployeeIndex]:
    roster: dict[str, dict[date, RosterEntryView]] = defaultdict(dict)
    for entry in inputs.roster:
        roster[entry.employee_id][entry.work_date] = RosterEntryView(
            state=(
                ResultRosterState.WORK
                if entry.state is RosterState.WORK
                else ResultRosterState.REST
            ),
            shifts=entry.shifts,
            rules=entry.rules,
        )

    adjacent_work: dict[str, set[date]] = defaultdict(set)
    for entry in inputs.adjacent_roster:
        if entry.state is RosterState.WORK:
            adjacent_work[entry.employee_id].add(entry.work_date)

    punches: dict[str, dict[date, list[Punch]]] = defaultdict(lambda: defaultdict(list))
    for punch in inputs.punches:
        punches[punch.employee_id][punch.attendance_date].append(
            replace(punch, punch_time=ensure_aware(punch.punch_time))
        )

    trips: dict[str, list[Trip]] = defaultdict(list)
    for trip in inputs.trips:
        trips[trip.employee_id].append(
            replace(
                trip,
                start_at=ensure_aware(trip.start_at),
                end_at=ensure_aware(trip.end_at),
            )
        )

    overtime: dict[str, dict[date, int]] = defaultdict(lambda: defaultdict(int))
    for overtime_day in inputs.overtime_days:
        overtime[overtime_day.employee_id][overtime_day.work_date] += (
            overtime_day.minutes
        )

    indexes: dict[str, _EmployeeIndex] = {}
    for employee in inputs.employees:
        employee_id = employee.employee_id
        employee_roster = roster.get(employee_id, {})
        shifts_by_date = {
            day: entry.shifts
            for day, entry in employee_roster.items()
            if entry.state is ResultRosterState.WORK and entry.shifts
        }
        instances = build_shift_instances(shifts_by_date)
        employee_punches = {
            day: tuple(day_punches)
            for day, day_punches in punches.get(employee_id, {}).items()
        }
        employee_trips = tuple(trips.get(employee_id, ()))
        employee_overtime = dict(overtime.get(employee_id, {}))
        work_dates = {
            day
            for day, entry in employee_roster.items()
            if entry.state is ResultRosterState.WORK
        }
        work_dates.update(adjacent_work.get(employee_id, set()))
        allocation = allocate_leave(
            tuple(leave for leave in inputs.leaves if leave.employee_id == employee_id),
            frozenset(work_dates),
            month_start,
            month_end,
        )
        data_dates: set[date] = set(employee_roster)
        data_dates.update(employee_punches)
        for trip in employee_trips:
            data_dates.update(dates_in(trip.start_at.date(), trip.end_at.date()))
        data_dates.update(employee_overtime)
        data_dates.update(allocation.by_date)
        data_dates.update(allocation.offset_minutes_by_date)
        data_dates.update(allocation.missing_work_start_minutes_by_date)
        indexes[employee_id] = _EmployeeIndex(
            employee_id=employee_id,
            roster=employee_roster,
            instances=instances,
            punches=employee_punches,
            trips=employee_trips,
            overtime=employee_overtime,
            leave=allocation,
            data_dates=frozenset(data_dates),
        )
    return indexes


def _day_type(work_date: date, holidays: Mapping[date, HolidayDayType]) -> DayType:
    if holidays.get(work_date) is HolidayDayType.ADJUSTED_WORKDAY:
        return DayType.WORKDAY
    if holidays.get(work_date) is HolidayDayType.HOLIDAY:
        return DayType.HOLIDAY
    if work_date.weekday() >= 5:
        return DayType.WEEKEND
    return DayType.WORKDAY


def _employment_bounds(
    employee: Employee, month_start: date, month_end: date
) -> tuple[date, date]:
    start = max(month_start, employee.hire_date)
    end = min(month_end, employee.resign_date or month_end)
    return start, end


def _has_month_data(index: _EmployeeIndex, start: date, end: date) -> bool:
    return any(start <= day <= end for day in index.data_dates)


def _day_keys(
    index: _EmployeeIndex,
    inputs: MonthInputs,
    start: date,
    end: date,
) -> list[date]:
    keys: set[date] = set()
    if inputs.roster_default is ResultRosterState.REST:
        keys.update(dates_in(start, end))
    keys.update(day for day in index.data_dates if start <= day <= end)
    return sorted(keys)


def _roster_state(
    day: date,
    index: _EmployeeIndex,
    default: ResultRosterState,
    default_rules: Rules,
) -> tuple[ResultRosterState, tuple[ShiftInstance, ...], Rules]:
    entry = index.roster.get(day)
    if entry is not None:
        return (
            entry.state,
            index.instances.get(day, ()),
            entry.rules or default_rules,
        )
    return default, (), default_rules


def _trips_on_day(trips: tuple[Trip, ...], day: date) -> tuple[Trip, ...]:
    return tuple(
        trip for trip in trips if trip.start_at.date() <= day <= trip.end_at.date()
    )


def _calculate_employee(
    index: _EmployeeIndex,
    inputs: MonthInputs,
    start: date,
    end: date,
    holidays: Mapping[date, HolidayDayType],
) -> list[DayComputation]:
    keys = _day_keys(index, inputs, start, end)
    computations: list[DayComputation] = []
    for day in keys:
        roster_state, instances, rules = _roster_state(
            day, index, inputs.roster_default, inputs.rules
        )
        context = DayContext(
            employee_id=index.employee_id,
            work_date=day,
            day_type=_day_type(day, holidays),
            roster_state=roster_state,
            instances=instances,
            punches=index.punches.get(day, ()),
            trips=_trips_on_day(index.trips, day),
            oa_ot_minutes=index.overtime.get(day, 0),
            leave=index.leave.by_date.get(day),
            offset_minutes=index.leave.offset_minutes_by_date.get(day, 0),
            missing_work_start_minutes=(
                index.leave.missing_work_start_minutes_by_date.get(day, 0)
            ),
            rules=rules,
        )
        computations.append(calculate_day(context))
    return computations


def _month_summary(
    employee_id: str, computations: list[DayComputation]
) -> MonthSummary:
    weekday_full = 0
    weekend_full = 0
    weekday_attended = Fraction(0)
    weekend_attended = Fraction(0)
    paid = Fraction(0)
    unpaid = Fraction(0)
    comp = Fraction(0)
    trip_days = Fraction(0)
    ot_weekday = 0
    ot_weekend = 0
    ot_holiday = 0
    applied_offset = 0
    unused = 0
    late_count = 0
    late_minutes = 0
    early_count = 0
    early_minutes = 0
    missing = 0
    absent_days = 0
    worked = 0
    attendance_deduct = Decimal(0)

    for computation in computations:
        result = computation.result
        if (
            result.day_type is DayType.WORKDAY
            and result.roster_state is ResultRosterState.WORK
        ):
            weekday_full += 1
        if (
            result.day_type is DayType.WEEKEND
            and result.roster_state is ResultRosterState.WORK
        ):
            weekend_full += 1
        if result.day_type is DayType.WORKDAY:
            weekday_attended += computation.attendance_fraction
        if result.day_type is DayType.WEEKEND:
            weekend_attended += computation.attendance_fraction
        if result.roster_state is ResultRosterState.WORK:
            paid += computation.paid_leave_days
            unpaid += computation.unpaid_leave_days
            comp += computation.comp_leave_days
            trip_days += computation.trip_fraction
        ot_weekday += result.ot_weekday_minutes
        ot_weekend += result.ot_weekend_minutes
        ot_holiday += result.ot_holiday_minutes
        applied_offset += computation.applied_comp_offset_minutes
        unused += result.comp_offset_unused_minutes
        late_count += result.late_count
        late_minutes += result.late_minutes
        early_count += result.early_count
        early_minutes += result.early_minutes
        missing += result.missing_punch_count
        if (
            result.day_status is DayStatus.ABSENT
            and computation.attendance_fraction == 0
        ):
            absent_days += 1
        worked += result.worked_minutes
        # Absent-day zeroing happens at the day grain (spec 7.10), so the
        # month total is the sum of the itemized day totals.
        attendance_deduct += result.deduction_total

    return MonthSummary(
        employee_id=employee_id,
        weekday_full=day_value(weekday_full),
        weekend_full=day_value(weekend_full),
        weekday_attended=day_value(weekday_attended),
        weekend_attended=day_value(weekend_attended),
        paid_leave_days=day_value(paid),
        unpaid_leave_days=day_value(unpaid),
        comp_leave_days=day_value(comp),
        trip_days=day_value(trip_days),
        ot_weekday_minutes=ot_weekday,
        ot_weekend_minutes=ot_weekend,
        ot_holiday_minutes=ot_holiday,
        ot_weekday_hours=hours_value(ot_weekday),
        ot_weekend_hours=hours_value(ot_weekend),
        ot_holiday_hours=hours_value(ot_holiday),
        comp_leave_used_hours=hours_value(applied_offset),
        comp_offset_unused_minutes=unused,
        late_count=late_count,
        late_minutes=late_minutes,
        early_count=early_count,
        early_minutes=early_minutes,
        missing_punch_count=missing,
        absent_days=absent_days,
        worked_minutes=worked,
        attendance_deduct=amount_value(attendance_deduct),
        is_adjusted=False,
        calc_version=CALC_VERSION,
    )


def _run_summary(
    inputs: MonthInputs,
    summaries: list[MonthSummary],
    day_results: list[DayResult],
    skipped_reasons: Counter[str],
) -> RunSummary:
    status_counts = Counter(str(result.day_status) for result in day_results)
    flag_counts: Counter[str] = Counter()
    for result in day_results:
        flag_counts.update(result.day_flags)
    attendance_deduct = sum(
        (summary.attendance_deduct for summary in summaries), Decimal(0)
    )
    return RunSummary(
        employees_total=len(inputs.employees),
        employees_calculated=len(summaries),
        employees_skipped=sum(skipped_reasons.values()),
        skipped_reasons=dict(skipped_reasons),
        days_total=len(day_results),
        days_by_status=dict(status_counts),
        flag_counts=dict(flag_counts),
        late_count=sum(summary.late_count for summary in summaries),
        late_minutes=sum(summary.late_minutes for summary in summaries),
        early_count=sum(summary.early_count for summary in summaries),
        early_minutes=sum(summary.early_minutes for summary in summaries),
        missing_punch_count=sum(summary.missing_punch_count for summary in summaries),
        absent_days=sum(summary.absent_days for summary in summaries),
        ot_weekday_minutes=sum(summary.ot_weekday_minutes for summary in summaries),
        ot_weekend_minutes=sum(summary.ot_weekend_minutes for summary in summaries),
        ot_holiday_minutes=sum(summary.ot_holiday_minutes for summary in summaries),
        comp_offset_unused_minutes=sum(
            summary.comp_offset_unused_minutes for summary in summaries
        ),
        attendance_deduct=amount_value(attendance_deduct),
    )


def run_month(inputs: MonthInputs) -> MonthOutputs:
    """Calculate one company-month from frozen contract inputs.

    The function is pure: it never opens a session and never mutates its
    inputs. Roster entries are authoritative; plans are never re-resolved.
    """
    month_start, month_end = month_bounds(inputs.month)
    holidays = {holiday.date: holiday.day_type for holiday in inputs.holidays}
    indexes = _index_inputs(inputs, month_start, month_end)

    day_results: list[DayResult] = []
    summaries: list[MonthSummary] = []
    skipped: Counter[str] = Counter()

    for employee in inputs.employees:
        start, end = _employment_bounds(employee, month_start, month_end)
        if start > end:
            skipped[_OUT_OF_EMPLOYMENT_REASON] += 1
            continue
        index = indexes[employee.employee_id]
        if not _has_month_data(index, start, end):
            skipped[_NO_DATA_REASON] += 1
            continue
        computations = _calculate_employee(index, inputs, start, end, holidays)
        if not computations:
            skipped[_NO_DATA_REASON] += 1
            continue
        day_results.extend(computation.result for computation in computations)
        summaries.append(_month_summary(employee.employee_id, computations))

    return MonthOutputs(
        day_results=tuple(day_results),
        month_summaries=tuple(summaries),
        summary=_run_summary(inputs, summaries, day_results, skipped),
    )
