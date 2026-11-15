"""Leave allocation and comp-time offset targets (spec sections 7.4 and 7.6.4)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction

from app.enums import LeaveKind
from app.services.attendance.calc._common import (
    dates_in,
    ensure_aware,
    to_fraction,
)
from app.services.attendance.calc.models import MINUTES_PER_COMP_DAY, Leave

_KIND_PRIORITY = (LeaveKind.PAID, LeaveKind.COMP, LeaveKind.UNPAID)

# ``leave_range_uncovered`` exists in the flag vocabulary but neither the
# calculation spec nor any golden case defines a trigger: allocation fans a
# request across every scheduled day in its range, so no covered day is left
# uncovered. Excess and non-workday coverage are emitted as
# ``leave_days_excess`` / ``leave_on_non_workday``.


@dataclass(frozen=True, slots=True)
class DayLeave:
    kind: LeaveKind | None
    requests: tuple[Leave, ...]
    days: Mapping[LeaveKind, Fraction]
    intervals: tuple[tuple[datetime, datetime], ...]
    on_non_workday: bool
    days_excess: bool

    @property
    def total_days(self) -> Fraction:
        return sum(self.days.values(), Fraction(0))


@dataclass(frozen=True, slots=True)
class LeaveAllocation:
    by_date: Mapping[date, DayLeave]
    offset_minutes_by_date: Mapping[date, int]
    missing_work_start_minutes_by_date: Mapping[date, int]


def _dominant_kind(requests: tuple[Leave, ...]) -> LeaveKind | None:
    present = {request.leave_kind for request in requests}
    for kind in _KIND_PRIORITY:
        if kind in present:
            return kind
    return None


def _cap_by_priority(raw: dict[LeaveKind, Fraction]) -> dict[LeaveKind, Fraction]:
    remaining = Fraction(1)
    capped: dict[LeaveKind, Fraction] = {}
    for kind in _KIND_PRIORITY:
        amount = min(raw.get(kind, Fraction(0)), remaining)
        capped[kind] = amount
        remaining -= amount
    return capped


def allocate_leave(
    leaves: tuple[Leave, ...],
    scheduled_work_dates: frozenset[date],
    month_start: date,
    month_end: date,
) -> LeaveAllocation:
    """Allocate each request across the scheduled days in its full rest interval.

    The denominator reads adjacent-month roster data so a cross-month request
    never duplicates days; only dates inside ``month_start..month_end`` produce
    day annotations.
    """
    raw_days: dict[date, dict[LeaveKind, Fraction]] = {}
    requests_by_date: dict[date, list[Leave]] = {}
    intervals_by_date: dict[date, list[tuple[datetime, datetime]]] = {}
    non_workday_dates: set[date] = set()
    excess_dates: set[date] = set()
    offset_minutes: dict[date, int] = {}
    missing_work_start: dict[date, int] = {}

    for leave in leaves:
        rest_start = ensure_aware(leave.rest_start_at)
        rest_end = ensure_aware(leave.rest_end_at)
        interval_dates = dates_in(rest_start.date(), rest_end.date())
        covered = [day for day in interval_dates if day in scheduled_work_dates]
        days = to_fraction(leave.days)
        per_day = min(Fraction(1), days / len(covered)) if covered else Fraction(0)
        excess = max(Fraction(0), days - len(covered))

        for day in interval_dates:
            if not month_start <= day <= month_end:
                continue
            requests_by_date.setdefault(day, []).append(leave)
            intervals_by_date.setdefault(day, []).append((rest_start, rest_end))
            if day in scheduled_work_dates:
                raw_days.setdefault(day, {})
                raw_days[day][leave.leave_kind] = (
                    raw_days[day].get(leave.leave_kind, Fraction(0)) + per_day
                )
                if excess > 0:
                    excess_dates.add(day)
            else:
                non_workday_dates.add(day)

        if leave.leave_kind is not LeaveKind.COMP:
            continue
        comp_minutes = int(days * MINUTES_PER_COMP_DAY)
        if leave.work_start_at is None:
            target = rest_start.date()
            if not month_start <= target <= month_end:
                in_month = [
                    day for day in interval_dates if month_start <= day <= month_end
                ]
                if not in_month:
                    continue
                target = in_month[0]
            missing_work_start[target] = (
                missing_work_start.get(target, 0) + comp_minutes
            )
        else:
            target = ensure_aware(leave.work_start_at).date()
            if month_start <= target <= month_end:
                offset_minutes[target] = offset_minutes.get(target, 0) + comp_minutes

    by_date: dict[date, DayLeave] = {}
    for day, requests in requests_by_date.items():
        tuple_requests = tuple(requests)
        by_date[day] = DayLeave(
            kind=_dominant_kind(tuple_requests),
            requests=tuple_requests,
            days=_cap_by_priority(raw_days.get(day, {})),
            intervals=tuple(intervals_by_date.get(day, [])),
            on_non_workday=day in non_workday_dates,
            days_excess=day in excess_dates,
        )

    return LeaveAllocation(
        by_date=by_date,
        offset_minutes_by_date=offset_minutes,
        missing_work_start_minutes_by_date=missing_work_start,
    )
