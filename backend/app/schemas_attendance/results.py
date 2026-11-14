"""Result schemas: day results, shift results, summaries, and adjustments."""

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic import Field, model_validator
from sqlmodel import SQLModel

from app.enums import (
    AdjustmentStatus,
    DayStatus,
    DayType,
    LeaveKind,
    ResultRosterState,
    TripKind,
)
from app.schemas_attendance.common import (
    DecimalString,
    EmployeeDisplay,
    MonthString,
    ReadModel,
    WriteModel,
)
from app.schemas_attendance.imports import (
    OaLeavePublic,
    OaOvertimeDayPublic,
    OaTripPublic,
    PunchRecordPublic,
)
from app.schemas_attendance.scheduling import RosterEntryPublic

ABNORMAL_DAY_STATUSES = frozenset(
    {
        DayStatus.LATE,
        DayStatus.EARLY,
        DayStatus.MISSING_PUNCH,
        DayStatus.ABSENT,
        DayStatus.UNSCHEDULED_ATTENDANCE,
    }
)
ABNORMAL_DAY_FLAGS = frozenset(
    {
        "leave_trip_conflict",
        "leave_ot_conflict",
        "punch_during_leave",
        "out_of_window_punch",
    }
)


def derive_is_abnormal(day_status: DayStatus, day_flags: list[str]) -> bool:
    """Derive the anomaly view flag exactly as section 8.3.5 defines it."""
    return day_status in ABNORMAL_DAY_STATUSES or bool(
        ABNORMAL_DAY_FLAGS.intersection(day_flags)
    )


class AttendanceDayShiftResultPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    day_result_id: uuid.UUID
    calc_run_id: uuid.UUID
    employee_id: uuid.UUID
    work_date: date
    seq: int
    shift_id: uuid.UUID
    shift_code: str
    shift_name: str
    start_time: time
    end_time: time
    cross_day: bool
    break_start: time | None = None
    break_end: time | None = None
    rest_minutes: int
    shift_status: DayStatus
    shift_flags: list[str] = []
    punch_in_at: datetime | None = None
    punch_out_at: datetime | None = None
    break_out_at: datetime | None = None
    break_in_at: datetime | None = None
    scheduled_minutes: int
    worked_minutes: int
    late_minutes: int
    early_minutes: int
    missing_punch_count: int
    ot_minutes: int
    comp_offset_minutes: int
    leave_days: DecimalString
    note: str | None = None


class AttendanceDayResultPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    attendance_month_id: uuid.UUID
    calc_run_id: uuid.UUID
    employee_id: uuid.UUID
    employee_no: str | None = None
    employee_name: str | None = None
    department_name: str | None = None
    work_date: date
    day_type: DayType
    roster_state: ResultRosterState
    day_status: DayStatus
    day_flags: list[str] = []
    is_abnormal: bool = False
    attendance_fraction: DecimalString
    scheduled_minutes: int
    worked_minutes: int
    late_minutes: int
    early_minutes: int
    late_count: int
    early_count: int
    missing_punch_count: int
    leave_kind: LeaveKind | None = None
    leave_days: DecimalString
    paid_leave_days: DecimalString
    unpaid_leave_days: DecimalString
    comp_leave_days: DecimalString
    trip_kind: TripKind | None = None
    trip_fraction: DecimalString
    ot_weekday_minutes: int
    ot_weekend_minutes: int
    ot_holiday_minutes: int
    comp_offset_minutes: int
    comp_offset_unused_minutes: int
    absent_deduct_amount: DecimalString
    late_deduct_amount: DecimalString
    early_deduct_amount: DecimalString
    missing_punch_deduct_amount: DecimalString
    deduction_total: DecimalString
    is_adjusted: bool
    adjustment_id: uuid.UUID | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _derive_is_abnormal(self) -> AttendanceDayResultPublic:
        self.is_abnormal = derive_is_abnormal(self.day_status, self.day_flags)
        return self


class AttendanceDayResultsPublic(SQLModel):
    data: list[AttendanceDayResultPublic]
    count: int


class AttendanceMonthSummaryPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    attendance_month_id: uuid.UUID
    calc_run_id: uuid.UUID
    employee_id: uuid.UUID
    employee_no: str | None = None
    employee_name: str | None = None
    department_name: str | None = None
    weekday_full: DecimalString
    weekend_full: DecimalString
    weekday_attended: DecimalString
    weekend_attended: DecimalString
    paid_leave_days: DecimalString
    unpaid_leave_days: DecimalString
    comp_leave_days: DecimalString
    trip_days: DecimalString
    ot_weekday_minutes: int
    ot_weekend_minutes: int
    ot_holiday_minutes: int
    ot_weekday_hours: DecimalString
    ot_weekend_hours: DecimalString
    ot_holiday_hours: DecimalString
    comp_leave_used_hours: DecimalString
    comp_offset_unused_minutes: int
    late_count: int
    late_minutes: int
    early_count: int
    early_minutes: int
    missing_punch_count: int
    absent_days: int
    worked_minutes: int
    attendance_deduct: DecimalString
    is_adjusted: bool
    calc_version: str
    rules_version: str
    created_at: datetime


class AttendanceMonthSummariesPublic(SQLModel):
    data: list[AttendanceMonthSummaryPublic]
    count: int


class AttendanceAdjustmentValues(WriteModel):
    day_status: DayStatus | None = None
    attendance_fraction: DecimalString | None = Field(default=None, ge=0, le=1)
    worked_minutes: int | None = Field(default=None, ge=0)
    ot_weekday_minutes: int | None = Field(default=None, ge=0)
    ot_weekend_minutes: int | None = Field(default=None, ge=0)
    ot_holiday_minutes: int | None = Field(default=None, ge=0)
    late_minutes: int | None = Field(default=None, ge=0)
    early_minutes: int | None = Field(default=None, ge=0)
    missing_punch_count: int | None = Field(default=None, ge=0)
    leave_days: DecimalString | None = Field(default=None, ge=0, le=1)
    note: str | None = Field(default=None, max_length=500)


class AttendanceAdjustmentCreate(WriteModel):
    company_id: uuid.UUID
    employee_id: uuid.UUID
    work_date: date
    base_version: int = Field(ge=0)
    adjusted_values: AttendanceAdjustmentValues
    reason: str = Field(min_length=1, max_length=500)


class AttendanceAdjustmentPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    attendance_month_id: uuid.UUID
    employee_id: uuid.UUID
    work_date: date
    version: int
    status: AdjustmentStatus
    original_values: dict[str, Any]
    adjusted_values: dict[str, Any]
    reason: str
    adjusted_by: uuid.UUID
    adjusted_by_name: str | None = None
    adjusted_at: datetime
    calc_run_id: uuid.UUID


class AttendanceAdjustmentsPublic(SQLModel):
    data: list[AttendanceAdjustmentPublic]
    count: int


class AttendanceDayDetailPublic(SQLModel):
    day_result: AttendanceDayResultPublic
    shift_results: list[AttendanceDayShiftResultPublic]
    roster_entry: RosterEntryPublic | None = None
    punches: list[PunchRecordPublic] = []
    oa_trips: list[OaTripPublic] = []
    oa_overtime_days: list[OaOvertimeDayPublic] = []
    oa_leaves: list[OaLeavePublic] = []
    adjustments: list[AttendanceAdjustmentPublic] = []


class EmployeeResultCalendarPublic(SQLModel):
    employee: EmployeeDisplay
    month: MonthString
    summary: AttendanceMonthSummaryPublic | None = None
    days: list[AttendanceDayResultPublic] = []
