"""Per-day attendance calculation (spec sections 7.2 to 7.10)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from fractions import Fraction

from app.enums import (
    DayStatus,
    DayType,
    LeaveKind,
    ResultRosterState,
    TripKind,
)
from app.services.attendance.calc._common import (
    amount_value,
    day_value,
    minutes_between,
    minutes_value,
    overlap_minutes,
)
from app.services.attendance.calc.leave import DayLeave
from app.services.attendance.calc.models import (
    MAX_OA_OT_MINUTES,
    DayResult,
    Punch,
    Rules,
    ShiftResult,
    Trip,
)
from app.services.attendance.calc.punching import (
    ShiftInstance,
    ShiftMatch,
    is_out_of_window,
    match_shift,
    overtime_cap,
    shift_leave_overlap,
)

_LEAVE_STATUS = {
    LeaveKind.PAID: DayStatus.PAID_LEAVE,
    LeaveKind.UNPAID: DayStatus.PERSONAL_LEAVE,
    LeaveKind.COMP: DayStatus.COMP_LEAVE,
}
_TRIP_STATUS = {
    TripKind.OUT: DayStatus.TRIP_OUT,
    TripKind.BUSINESS: DayStatus.TRIP_BUSINESS,
}

# Spec 7.8: full-day leave > absent > missing punch > late > early >
# trip/outing > overtime > normal > rest. Equal-rank statuses keep the first
# shift's kind (the three leave statuses share one rank).
_STATUS_PRIORITY = {
    DayStatus.PAID_LEAVE: 0,
    DayStatus.PERSONAL_LEAVE: 0,
    DayStatus.COMP_LEAVE: 0,
    DayStatus.ABSENT: 1,
    DayStatus.MISSING_PUNCH: 2,
    DayStatus.LATE: 3,
    DayStatus.EARLY: 4,
    DayStatus.TRIP_OUT: 5,
    DayStatus.TRIP_BUSINESS: 5,
    DayStatus.OVERTIME: 6,
    DayStatus.NORMAL: 7,
}


@dataclass(frozen=True, slots=True)
class DayContext:
    employee_id: str
    work_date: date
    day_type: DayType
    roster_state: ResultRosterState
    instances: tuple[ShiftInstance, ...]
    punches: tuple[Punch, ...]
    trips: tuple[Trip, ...]
    oa_ot_minutes: int
    leave: DayLeave | None
    offset_minutes: int
    missing_work_start_minutes: int
    rules: Rules


@dataclass(frozen=True, slots=True)
class DayComputation:
    """A day result plus the exact values month summaries aggregate."""

    result: DayResult
    attendance_fraction: Fraction
    paid_leave_days: Fraction
    unpaid_leave_days: Fraction
    comp_leave_days: Fraction
    trip_fraction: Fraction
    applied_comp_offset_minutes: int


def _shift_leave_days(
    index: int,
    instances: tuple[ShiftInstance, ...],
    leave_total: Fraction,
) -> Fraction:
    total_scheduled = sum(instance.scheduled_minutes for instance in instances)
    if total_scheduled <= 0:
        return Fraction(0)
    return min(
        Fraction(1),
        leave_total * instances[index].scheduled_minutes / total_scheduled,
    )


def _shift_trip_fraction(instance: ShiftInstance, trips: tuple[Trip, ...]) -> Fraction:
    span = instance.span_minutes
    if span <= 0:
        return Fraction(0)
    # Union-like overlap: sum per trip. Overlapping approvals are not expected
    # from import, and the cap below keeps the fraction in range.
    overlap = sum(
        overlap_minutes(instance.start_at, instance.end_at, trip.start_at, trip.end_at)
        for trip in trips
    )
    return min(Fraction(1), Fraction(overlap, span))


def _day_trip_fraction(
    instances: tuple[ShiftInstance, ...], trips: tuple[Trip, ...]
) -> Fraction:
    total_scheduled = sum(instance.scheduled_minutes for instance in instances)
    if total_scheduled <= 0:
        return Fraction(0)
    weighted = Fraction(0)
    for instance in instances:
        weighted += _shift_trip_fraction(instance, trips) * instance.scheduled_minutes
    return Fraction(weighted, total_scheduled)


def _trip_kind(
    instances: tuple[ShiftInstance, ...], trips: tuple[Trip, ...]
) -> TripKind:
    business = sum(
        _shift_trip_fraction(instance, (trip,))
        for instance in instances
        for trip in trips
        if trip.kind is TripKind.BUSINESS
    )
    outing = sum(
        _shift_trip_fraction(instance, (trip,))
        for instance in instances
        for trip in trips
        if trip.kind is TripKind.OUT
    )
    if business == 0 and outing == 0:
        return (
            TripKind.BUSINESS
            if any(trip.kind is TripKind.BUSINESS for trip in trips)
            else TripKind.OUT
        )
    return TripKind.BUSINESS if business >= outing else TripKind.OUT


def _overtime_bucket(day_type: DayType, roster_state: ResultRosterState) -> str:
    if day_type is DayType.HOLIDAY:
        return "holiday"
    if roster_state is ResultRosterState.WORK:
        return "weekday" if day_type is DayType.WORKDAY else "weekend"
    return "weekend"


def _shift_outcome(
    instance: ShiftInstance,
    match: ShiftMatch,
    ctx: DayContext,
    *,
    full_leave: bool,
    leave_total: Fraction,
    shift_leave: Fraction,
    trip_fraction: Fraction,
    trip_present: bool,
    has_oa: bool,
    leave_kind: LeaveKind | None,
) -> tuple[ShiftResult, Fraction, int]:
    """Return the shift result, its attendance credit, and its overtime minutes."""
    has_in = match.punch_in is not None
    has_out = match.punch_out is not None
    has_punch = has_in or has_out
    leave_fraction = min(Fraction(1), leave_total)
    late_minutes = 0
    early_minutes = 0
    worked_minutes = 0
    missing = 0
    flags: set[str] = set()
    credit = Fraction(0)
    punch_ot = 0

    if full_leave:
        status = _LEAVE_STATUS[leave_kind or LeaveKind.UNPAID]
        flags.add("leave")
    elif has_punch:
        if has_in and has_out:
            start = instance.start_at
            end = instance.end_at
            raw_worked = (
                minutes_between(
                    match.punch_in.punch_time,  # type: ignore[union-attr]
                    min(match.punch_out.punch_time, end),  # type: ignore[union-attr]
                )
                - instance.definition.rest_minutes
            )
            worked_minutes = max(0, raw_worked)
            if leave_total > 0 and ctx.leave is not None:
                worked_minutes = max(
                    0,
                    worked_minutes - shift_leave_overlap(instance, ctx.leave.intervals),
                )
            late_minutes = max(
                0,
                minutes_between(start, match.punch_in.punch_time)  # type: ignore[union-attr]
                - ctx.rules.late_grace_min,
            )
            early_minutes = max(
                0,
                minutes_between(match.punch_out.punch_time, end)  # type: ignore[union-attr]
                - ctx.rules.early_grace_min,
            )
        missing = (0 if has_in else 1) + (0 if has_out else 1)
        if ctx.rules.break_punch_required and (
            instance.definition.break_start is not None
            and instance.definition.break_end is not None
        ):
            missing += match.break_missing
            if match.break_missing:
                flags.add("break_punch_missing")
        if missing:
            status = DayStatus.MISSING_PUNCH
            flags.add("missing_punch")
        elif late_minutes:
            status = DayStatus.LATE
            flags.add("late")
        elif early_minutes:
            status = DayStatus.EARLY
            flags.add("early")
        else:
            status = DayStatus.NORMAL
        credit = instance.scheduled_minutes * (1 - leave_fraction)
    elif trip_present and not has_oa:
        status = _TRIP_STATUS[_trip_kind(ctx.instances, ctx.trips)]
        flags.add("trip")
        usable = min(trip_fraction, 1 - leave_fraction)
        credit = instance.scheduled_minutes * usable
        worked_minutes = minutes_value(credit)
    elif has_oa:
        status = DayStatus.OVERTIME
        flags.add("overtime")
        credit = instance.scheduled_minutes * (1 - leave_fraction)
    elif leave_total > 0:
        # Partial leave with no punch/trip/OA evidence: the covered part is
        # exempt and the uncovered part counts as exactly two missing punches.
        status = DayStatus.MISSING_PUNCH
        flags.add("missing_punch")
        missing = 2 if instance.seq == 0 else 0
    elif ctx.rules.absent_if_no_punch:
        status = DayStatus.ABSENT
        flags.add("absent")
    else:
        status = DayStatus.MISSING_PUNCH
        flags.add("missing_punch")
        missing = 2 if instance.seq == 0 else 0

    if not full_leave and match.punch_out is not None:
        excess = minutes_between(instance.end_at, match.punch_out.punch_time)
        if excess >= ctx.rules.ot_threshold_min:
            punch_ot = min(excess, overtime_cap(instance, ctx.rules))

    result = ShiftResult(
        seq=instance.seq,
        shift_code=instance.definition.shift_code,
        shift_name=instance.definition.shift_name,
        start_time=instance.definition.start_time,
        end_time=instance.definition.end_time,
        cross_day=instance.definition.cross_day,
        break_start=instance.definition.break_start,
        break_end=instance.definition.break_end,
        rest_minutes=instance.definition.rest_minutes,
        shift_status=status,
        shift_flags=tuple(sorted(flags)),
        punch_in_at=(match.punch_in.punch_time if match.punch_in is not None else None),
        punch_out_at=(
            match.punch_out.punch_time if match.punch_out is not None else None
        ),
        break_out_at=(
            match.break_out.punch_time if match.break_out is not None else None
        ),
        break_in_at=(match.break_in.punch_time if match.break_in is not None else None),
        scheduled_minutes=instance.scheduled_minutes,
        worked_minutes=worked_minutes,
        late_minutes=late_minutes,
        early_minutes=early_minutes,
        missing_punch_count=missing,
        ot_minutes=punch_ot,
        comp_offset_minutes=0,
        leave_days=day_value(shift_leave),
    )
    return result, credit, punch_ot


def calculate_day(ctx: DayContext) -> DayComputation:
    leave_total = ctx.leave.total_days if ctx.leave is not None else Fraction(0)
    full_leave = leave_total >= 1
    leave_kind = ctx.leave.kind if ctx.leave is not None else None
    has_oa = ctx.oa_ot_minutes > 0
    trip_present = bool(ctx.trips)
    scheduled_work = ctx.roster_state is ResultRosterState.WORK and bool(ctx.instances)

    matches = tuple(
        match_shift(instance, ctx.punches, ctx.rules) for instance in ctx.instances
    )
    shift_results: list[ShiftResult] = []
    credits = Fraction(0)
    total_scheduled = 0
    punch_ot_total = 0
    late_count = 0
    early_count = 0
    late_minutes_total = 0
    early_minutes_total = 0
    missing_total = 0
    worked_total = 0

    for index, (instance, match) in enumerate(zip(ctx.instances, matches, strict=True)):
        shift_leave = (
            _shift_leave_days(index, ctx.instances, leave_total)
            if ctx.instances
            else Fraction(0)
        )
        shift_result, credit, punch_ot = _shift_outcome(
            instance,
            match,
            ctx,
            full_leave=full_leave,
            leave_total=leave_total,
            shift_leave=shift_leave,
            trip_fraction=_shift_trip_fraction(instance, ctx.trips),
            trip_present=trip_present,
            has_oa=has_oa,
            leave_kind=leave_kind,
        )
        shift_results.append(shift_result)
        credits += credit
        total_scheduled += instance.scheduled_minutes
        punch_ot_total = max(punch_ot_total, punch_ot)
        if shift_result.late_minutes:
            late_count += 1
            late_minutes_total += shift_result.late_minutes
        if shift_result.early_minutes:
            early_count += 1
            early_minutes_total += shift_result.early_minutes
        missing_total += shift_result.missing_punch_count
        worked_total += shift_result.worked_minutes

    any_valid_punch = any(match.has_valid_punch() for match in matches)
    if ctx.roster_state is ResultRosterState.WORK and total_scheduled > 0:
        attendance = min(Fraction(1), credits / total_scheduled)
    elif ctx.roster_state is ResultRosterState.WORK:
        attendance = Fraction(0)
    else:
        attendance = Fraction(1) if ctx.punches else Fraction(0)

    oa_ot = min(MAX_OA_OT_MINUTES, ctx.oa_ot_minutes)
    if full_leave:
        raw_ot = 0
    elif ctx.roster_state is ResultRosterState.WORK:
        raw_ot = min(ctx.rules.ot_max_min, max(punch_ot_total, oa_ot))
    else:
        raw_ot = oa_ot

    applied = min(raw_ot, ctx.offset_minutes)
    net_ot = raw_ot - applied
    unused = (ctx.offset_minutes - applied) + ctx.missing_work_start_minutes

    trip_fraction = _day_trip_fraction(ctx.instances, ctx.trips)
    trip_kind = _trip_kind(ctx.instances, ctx.trips) if trip_present else None

    flags: set[str] = set()
    for shift_result in shift_results:
        flags.update(shift_result.shift_flags)
    if late_count:
        flags.add("late")
    if early_count:
        flags.add("early")
    if missing_total:
        flags.add("missing_punch")
    if raw_ot > 0:
        flags.add("overtime")
    if oa_ot > 0 and not any_valid_punch:
        flags.add("oa_ot_only")
    if trip_present:
        flags.add("trip")
    if ctx.leave is not None:
        flags.add("leave")
        if full_leave and ctx.punches:
            flags.add("punch_during_leave")
        if trip_present:
            flags.add("leave_trip_conflict")
        if oa_ot > 0 or punch_ot_total > 0:
            flags.add("leave_ot_conflict")
        if len(ctx.leave.requests) > 1:
            flags.add("multiple_leave_requests")
        if ctx.leave.on_non_workday:
            flags.add("leave_on_non_workday")
        if ctx.leave.days_excess:
            flags.add("leave_days_excess")
    if ctx.offset_minutes > 0 and raw_ot == 0:
        flags.add("comp_offset_no_ot")
    if unused > 0:
        flags.add("comp_offset_unused")

    used_punches = {punch for match in matches for punch in match.used}
    windows = tuple(window for match in matches for window in match.windows)
    if ctx.instances:
        for punch in ctx.punches:
            if punch in used_punches:
                continue
            date_gap = abs((punch.punch_time.date() - ctx.work_date).days)
            if date_gap > 2 or is_out_of_window(punch, windows):
                flags.add("out_of_window_punch")

    if (
        scheduled_work
        and not any_valid_punch
        and ctx.leave is None
        and not trip_present
        and oa_ot == 0
    ):
        flags.add("no_valid_punch")

    day_status = _day_status(
        ctx=ctx,
        full_leave=full_leave,
        leave_kind=leave_kind,
        shift_results=tuple(shift_results),
        trip_present=trip_present,
        trip_kind=trip_kind,
        raw_ot=raw_ot,
    )
    if day_status is DayStatus.UNSCHEDULED_ATTENDANCE:
        flags.add("unscheduled_attendance")

    # An absent day no longer counts late/early/missing punches for deduction
    # (spec 7.10); the shift-level diagnostics stay visible on the day result.
    absent = day_status is DayStatus.ABSENT
    absent_deduct, late_deduct, early_deduct, missing_deduct = _deduction_amounts(
        ctx.rules,
        absent_days=1 if absent else 0,
        late_count=0 if absent else late_count,
        early_count=0 if absent else early_count,
        missing_count=0 if absent else missing_total,
    )
    deduction_total = absent_deduct + late_deduct + early_deduct + missing_deduct

    leave_days_by_kind = ctx.leave.days if ctx.leave is not None else {}
    paid_leave = leave_days_by_kind.get(LeaveKind.PAID, Fraction(0))
    unpaid_leave = leave_days_by_kind.get(LeaveKind.UNPAID, Fraction(0))
    comp_leave = leave_days_by_kind.get(LeaveKind.COMP, Fraction(0))

    bucket = _overtime_bucket(ctx.day_type, ctx.roster_state)
    ot_weekday = net_ot if bucket == "weekday" else 0
    ot_weekend = net_ot if bucket == "weekend" else 0
    ot_holiday = net_ot if bucket == "holiday" else 0

    distributed = _distribute_comp_offset(tuple(shift_results), applied)

    result = DayResult(
        employee_id=ctx.employee_id,
        work_date=ctx.work_date,
        day_type=ctx.day_type,
        roster_state=ctx.roster_state,
        day_status=day_status,
        day_flags=tuple(sorted(flags)),
        attendance_fraction=day_value(attendance),
        scheduled_minutes=total_scheduled,
        worked_minutes=worked_total,
        late_minutes=late_minutes_total,
        early_minutes=early_minutes_total,
        missing_punch_count=missing_total,
        leave_kind=leave_kind,
        leave_days=day_value(leave_total),
        paid_leave_days=day_value(paid_leave),
        unpaid_leave_days=day_value(unpaid_leave),
        comp_leave_days=day_value(comp_leave),
        trip_kind=trip_kind,
        trip_fraction=day_value(trip_fraction),
        ot_weekday_minutes=ot_weekday,
        ot_weekend_minutes=ot_weekend,
        ot_holiday_minutes=ot_holiday,
        comp_offset_minutes=applied,
        comp_offset_unused_minutes=unused,
        absent_deduct_amount=amount_value(absent_deduct),
        late_deduct_amount=amount_value(late_deduct),
        early_deduct_amount=amount_value(early_deduct),
        missing_punch_deduct_amount=amount_value(missing_deduct),
        deduction_total=amount_value(deduction_total),
        late_count=late_count,
        early_count=early_count,
        shift_results=distributed,
    )
    return DayComputation(
        result=result,
        attendance_fraction=attendance,
        paid_leave_days=paid_leave,
        unpaid_leave_days=unpaid_leave,
        comp_leave_days=comp_leave,
        trip_fraction=trip_fraction,
        applied_comp_offset_minutes=applied,
    )


def _distribute_comp_offset(
    shift_results: tuple[ShiftResult, ...], applied: int
) -> tuple[ShiftResult, ...]:
    """Deduct offset minutes from shifts in reverse order (spec 7.6.4)."""
    if applied <= 0 or not shift_results:
        return shift_results
    remaining = applied
    updated: list[ShiftResult] = []
    for shift_result in reversed(shift_results):
        take = min(remaining, shift_result.ot_minutes)
        updated.append(replace(shift_result, comp_offset_minutes=take))
        remaining -= take
    updated.reverse()
    return tuple(updated)


def _deduction_amounts(
    rules: Rules,
    *,
    absent_days: int,
    late_count: int,
    early_count: int,
    missing_count: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Apply the section 7.10 formula once for both day and month grains."""
    return (
        -rules.absent_deduct_per_day * absent_days,
        -rules.late_deduct_per_occurrence * late_count,
        -rules.early_deduct_per_occurrence * early_count,
        -rules.missing_punch_deduct_per_occurrence * missing_count,
    )


def _day_status(
    ctx: DayContext,
    *,
    full_leave: bool,
    leave_kind: LeaveKind | None,
    shift_results: tuple[ShiftResult, ...],
    trip_present: bool,
    trip_kind: TripKind | None,
    raw_ot: int,
) -> DayStatus:
    """Aggregate shift statuses by the section 7.8 priority."""
    if full_leave:
        return _LEAVE_STATUS[leave_kind or LeaveKind.UNPAID]
    if shift_results:
        return min(
            (shift.shift_status for shift in shift_results),
            key=lambda status: _STATUS_PRIORITY[status],
        )
    if trip_present:
        return _TRIP_STATUS[trip_kind or TripKind.OUT]
    if raw_ot > 0:
        return DayStatus.OVERTIME
    if ctx.punches:
        return DayStatus.UNSCHEDULED_ATTENDANCE
    return DayStatus.REST
