"""Frozen contract inputs and outputs for the attendance calculation kernel.

The dataclasses in this module are the boundary between the database adapter
(C2) and the pure calculation engine. They contain no SQLModel or session
state: the same inputs always produce the same outputs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from app.enums import (
    DayStatus,
    DayType,
    HolidayDayType,
    LeaveKind,
    ResultRosterState,
    RosterState,
    TripKind,
)

CALC_VERSION = "attendance-calc-v1"
MINUTES_PER_COMP_DAY = 480
MAX_OA_OT_MINUTES = 480


@dataclass(frozen=True, slots=True)
class Employee:
    employee_id: str
    employee_no: str
    name: str
    hire_date: date
    resign_date: date | None = None
    department: str | None = None


@dataclass(frozen=True, slots=True)
class ShiftSnapshot:
    """A roster entry's frozen copy of its shift template (ADR-0004).

    Later edits to the shift template must never change an existing roster
    entry, so calculation consumes the snapshot carried by the roster row.
    """

    shift_code: str
    shift_name: str
    start_time: time
    end_time: time
    cross_day: bool
    break_start: time | None
    break_end: time | None
    rest_minutes: int


@dataclass(frozen=True, slots=True)
class RosterEntry:
    employee_id: str
    work_date: date
    state: RosterState
    shifts: tuple[ShiftSnapshot, ...] = ()
    # Effective rules for this entry's plan; ``None`` inherits the month
    # default. Plans are never re-resolved here (ADR-0004).
    rules: Rules | None = None


@dataclass(frozen=True, slots=True)
class Punch:
    employee_id: str
    attendance_date: date
    punch_time: datetime
    punch_result: str = ""


@dataclass(frozen=True, slots=True)
class Trip:
    id: str
    approval_no: str
    employee_id: str
    kind: TripKind
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class OvertimeDay:
    id: str
    approval_no: str
    employee_id: str
    work_date: date
    minutes: int


@dataclass(frozen=True, slots=True)
class Leave:
    id: str
    approval_no: str
    employee_id: str
    leave_kind: LeaveKind
    days: Decimal
    rest_start_at: datetime
    rest_end_at: datetime
    work_start_at: datetime | None = None
    work_end_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Holiday:
    date: date
    name: str
    day_type: HolidayDayType


@dataclass(frozen=True, slots=True)
class Rules:
    punch_window_min: int
    late_cap_min: int
    early_cap_min: int
    ot_max_min: int
    late_grace_min: int
    early_grace_min: int
    ot_threshold_min: int
    absent_if_no_punch: bool
    break_punch_required: bool
    break_punch_tolerance_min: int
    absent_deduct_per_day: Decimal
    late_deduct_per_occurrence: Decimal
    early_deduct_per_occurrence: Decimal
    missing_punch_deduct_per_occurrence: Decimal


@dataclass(frozen=True, slots=True)
class MonthInputs:
    """Everything the calculation kernel may read for one company-month.

    ``Mapping`` is imported only for summary mappings below; roster shift
    identity travels on each :class:`RosterEntry` snapshot, never through a
    month-level code lookup (ADR-0004).
    """

    month: date
    employees: tuple[Employee, ...]
    roster: tuple[RosterEntry, ...]
    rules: Rules
    punches: tuple[Punch, ...] = ()
    trips: tuple[Trip, ...] = ()
    overtime_days: tuple[OvertimeDay, ...] = ()
    leaves: tuple[Leave, ...] = ()
    holidays: tuple[Holiday, ...] = ()
    adjacent_roster: tuple[RosterEntry, ...] = ()
    roster_default: ResultRosterState = ResultRosterState.UNSCHEDULED


@dataclass(frozen=True, slots=True)
class ShiftResult:
    seq: int
    shift_code: str
    shift_name: str
    start_time: time
    end_time: time
    cross_day: bool
    break_start: time | None
    break_end: time | None
    rest_minutes: int
    shift_status: DayStatus
    shift_flags: tuple[str, ...]
    punch_in_at: datetime | None
    punch_out_at: datetime | None
    break_out_at: datetime | None
    break_in_at: datetime | None
    scheduled_minutes: int
    worked_minutes: int
    late_minutes: int
    early_minutes: int
    missing_punch_count: int
    ot_minutes: int
    comp_offset_minutes: int
    leave_days: Decimal


@dataclass(frozen=True, slots=True)
class DayResult:
    employee_id: str
    work_date: date
    day_type: DayType
    roster_state: ResultRosterState
    day_status: DayStatus
    day_flags: tuple[str, ...]
    attendance_fraction: Decimal
    scheduled_minutes: int
    worked_minutes: int
    late_minutes: int
    early_minutes: int
    missing_punch_count: int
    leave_kind: LeaveKind | None
    leave_days: Decimal
    paid_leave_days: Decimal
    unpaid_leave_days: Decimal
    comp_leave_days: Decimal
    trip_kind: TripKind | None
    trip_fraction: Decimal
    ot_weekday_minutes: int
    ot_weekend_minutes: int
    ot_holiday_minutes: int
    comp_offset_minutes: int
    comp_offset_unused_minutes: int
    absent_deduct_amount: Decimal
    late_deduct_amount: Decimal
    early_deduct_amount: Decimal
    missing_punch_deduct_amount: Decimal
    deduction_total: Decimal
    late_count: int
    early_count: int
    shift_results: tuple[ShiftResult, ...]


@dataclass(frozen=True, slots=True)
class MonthSummary:
    employee_id: str
    weekday_full: Decimal
    weekend_full: Decimal
    weekday_attended: Decimal
    weekend_attended: Decimal
    paid_leave_days: Decimal
    unpaid_leave_days: Decimal
    comp_leave_days: Decimal
    trip_days: Decimal
    ot_weekday_minutes: int
    ot_weekend_minutes: int
    ot_holiday_minutes: int
    ot_weekday_hours: Decimal
    ot_weekend_hours: Decimal
    ot_holiday_hours: Decimal
    comp_leave_used_hours: Decimal
    comp_offset_unused_minutes: int
    late_count: int
    late_minutes: int
    early_count: int
    early_minutes: int
    missing_punch_count: int
    absent_days: int
    worked_minutes: int
    attendance_deduct: Decimal
    is_adjusted: bool
    calc_version: str


@dataclass(frozen=True, slots=True)
class RunSummary:
    employees_total: int
    employees_calculated: int
    employees_skipped: int
    skipped_reasons: Mapping[str, int]
    days_total: int
    days_by_status: Mapping[str, int]
    flag_counts: Mapping[str, int]
    late_count: int
    late_minutes: int
    early_count: int
    early_minutes: int
    missing_punch_count: int
    absent_days: int
    ot_weekday_minutes: int
    ot_weekend_minutes: int
    ot_holiday_minutes: int
    comp_offset_unused_minutes: int
    attendance_deduct: Decimal


@dataclass(frozen=True, slots=True)
class MonthOutputs:
    day_results: tuple[DayResult, ...]
    month_summaries: tuple[MonthSummary, ...]
    summary: RunSummary
