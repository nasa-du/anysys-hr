"""Punch-to-shift matching (spec section 7.3)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from app.services.attendance.calc._common import (
    at,
    minutes_between,
    overlap_minutes,
)
from app.services.attendance.calc.models import (
    Punch,
    Rules,
    ShiftSnapshot,
)

_ONE_DAY = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class PunchWindow:
    start: datetime
    end: datetime

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment <= self.end


@dataclass(frozen=True, slots=True)
class ShiftInstance:
    definition: ShiftSnapshot
    work_date: date
    seq: int
    start_at: datetime
    end_at: datetime
    is_last: bool
    next_start_at: datetime | None

    @property
    def scheduled_minutes(self) -> int:
        span = minutes_between(self.start_at, self.end_at)
        return max(0, span - self.definition.rest_minutes)

    @property
    def span_minutes(self) -> int:
        return max(0, minutes_between(self.start_at, self.end_at))


@dataclass(frozen=True, slots=True)
class ShiftMatch:
    punch_in: Punch | None
    punch_out: Punch | None
    break_out: Punch | None
    break_in: Punch | None
    break_missing: int
    used: frozenset[Punch]
    windows: tuple[PunchWindow, ...]

    def has_valid_punch(self) -> bool:
        return self.punch_in is not None or self.punch_out is not None


def overtime_cap(instance: ShiftInstance, rules: Rules) -> int:
    """Out-window extension for the last shift of a day (spec 7.3.1)."""
    if not instance.is_last:
        return 0
    cap = rules.ot_max_min
    if instance.next_start_at is not None:
        gap = minutes_between(instance.end_at, instance.next_start_at)
        cap = min(cap, gap - rules.punch_window_min - 1)
    return max(0, cap)


def build_shift_instances(
    shifts_by_date: Mapping[date, tuple[ShiftSnapshot, ...]],
) -> dict[date, tuple[ShiftInstance, ...]]:
    """Instantiate every roster shift snapshot, including cross-day end times."""
    flat: list[ShiftInstance] = []
    for work_date in sorted(shifts_by_date):
        for seq, definition in enumerate(shifts_by_date[work_date]):
            end_date = work_date + _ONE_DAY if definition.cross_day else work_date
            flat.append(
                ShiftInstance(
                    definition=definition,
                    work_date=work_date,
                    seq=seq,
                    start_at=at(work_date, definition.start_time),
                    end_at=at(end_date, definition.end_time),
                    is_last=False,
                    next_start_at=None,
                )
            )

    flat.sort(key=lambda instance: (instance.work_date, instance.seq))
    resolved: list[ShiftInstance] = []
    for index, instance in enumerate(flat):
        next_instance = flat[index + 1] if index + 1 < len(flat) else None
        is_last = next_instance is None or next_instance.work_date != instance.work_date
        resolved.append(
            replace(
                instance,
                is_last=is_last,
                next_start_at=(
                    next_instance.start_at if next_instance is not None else None
                ),
            )
        )

    by_date: dict[date, list[ShiftInstance]] = {}
    for instance in resolved:
        by_date.setdefault(instance.work_date, []).append(instance)
    return {work_date: tuple(instances) for work_date, instances in by_date.items()}


def _time_at(instance: ShiftInstance, clock: time) -> datetime:
    moment = at(instance.work_date, clock)
    if moment < instance.start_at:
        moment += _ONE_DAY
    return moment


def _break_bounds(instance: ShiftInstance) -> tuple[datetime, datetime] | None:
    definition = instance.definition
    if definition.break_start is None or definition.break_end is None:
        return None
    start = _time_at(instance, definition.break_start)
    end = _time_at(instance, definition.break_end)
    if end < start:
        end += _ONE_DAY
    return start, end


def match_shift(
    instance: ShiftInstance, punches: tuple[Punch, ...], rules: Rules
) -> ShiftMatch:
    in_window = PunchWindow(
        start=instance.start_at - timedelta(minutes=rules.punch_window_min),
        end=instance.start_at + timedelta(minutes=rules.late_cap_min),
    )
    out_window = PunchWindow(
        start=instance.end_at - timedelta(minutes=rules.early_cap_min),
        end=instance.end_at + timedelta(minutes=overtime_cap(instance, rules)),
    )

    windows = [in_window, out_window]
    break_out: Punch | None = None
    break_in: Punch | None = None
    break_missing = 0
    break_punches: frozenset[Punch] = frozenset()
    break_bounds = _break_bounds(instance)
    if break_bounds is not None:
        break_start, break_end = break_bounds
        tolerance = timedelta(minutes=rules.break_punch_tolerance_min)
        break_window = PunchWindow(
            start=break_start - tolerance, end=break_end + tolerance
        )
        # Break punches are ignored entirely when validation is disabled, so
        # they must still count as known windows for out-of-window checks.
        windows.append(break_window)
        if rules.break_punch_required:
            # Identify break punches first: they must never drive late/early.
            candidates = [
                punch for punch in punches if break_window.contains(punch.punch_time)
            ]
            if candidates:
                break_out = min(
                    candidates,
                    key=lambda punch: abs(
                        minutes_between(break_start, punch.punch_time)
                    ),
                )
                remaining = [punch for punch in candidates if punch is not break_out]
                if remaining:
                    break_in = min(
                        remaining,
                        key=lambda punch: abs(
                            minutes_between(break_end, punch.punch_time)
                        ),
                    )
            break_punches = frozenset(
                punch for punch in (break_out, break_in) if punch is not None
            )
            break_missing = (0 if break_out else 1) + (0 if break_in else 1)

    in_candidates = [
        punch
        for punch in punches
        if punch not in break_punches and in_window.contains(punch.punch_time)
    ]
    out_candidates = [
        punch
        for punch in punches
        if punch not in break_punches and out_window.contains(punch.punch_time)
    ]
    punch_in = min(in_candidates, key=lambda punch: punch.punch_time, default=None)
    punch_out = max(out_candidates, key=lambda punch: punch.punch_time, default=None)

    used = frozenset(
        punch
        for punch in (punch_in, punch_out, break_out, break_in)
        if punch is not None
    )
    return ShiftMatch(
        punch_in=punch_in,
        punch_out=punch_out,
        break_out=break_out,
        break_in=break_in,
        break_missing=break_missing,
        used=used,
        windows=tuple(windows),
    )


def is_out_of_window(punch: Punch, windows: tuple[PunchWindow, ...]) -> bool:
    return not any(window.contains(punch.punch_time) for window in windows)


def shift_leave_overlap(
    instance: ShiftInstance,
    intervals: tuple[tuple[datetime, datetime], ...],
) -> int:
    """Minutes of leave that fall inside a shift's span."""
    return sum(
        overlap_minutes(instance.start_at, instance.end_at, start, end)
        for start, end in intervals
    )
