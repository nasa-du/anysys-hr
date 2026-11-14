"""Core attendance schemas: shifts, holidays, rules, months, and calc runs."""

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AfterValidator, Field, field_validator
from sqlmodel import SQLModel
from sqlmodel._compat import SQLModelConfig

from app.enums import (
    AttendanceMonthStatus,
    CalcRunStatus,
    CalcRunTrigger,
    HolidayDayType,
)
from app.schemas_attendance.common import (
    DecimalString,
    MonthString,
    ReadModel,
    WriteModel,
)
from app.services.common import normalize_code

SHIFT_CODE_PATTERN = r"^[A-Z0-9_-]{1,32}$"
COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"

# Rule integers are PostgreSQL ``INTEGER`` columns and amounts are
# ``NUMERIC(14, 2)``. Reject values the database cannot store as a 422 rather
# than letting the driver raise a 500 on commit.
MAX_RULE_MINUTES = 2_147_483_647
MAX_RULE_AMOUNT = Decimal("999999999999.99")


def _contract_shift_time(value: time) -> time:
    """Shift times are naive HH:MM:SS values without fractional seconds."""
    if value.tzinfo is not None:
        raise ValueError("时间不能包含时区")
    if value.microsecond:
        raise ValueError("时间不能包含小数秒")
    return value


ShiftTime = Annotated[time, AfterValidator(_contract_shift_time)]


class RuleValues(SQLModel):
    """A complete effective rule set."""

    punch_window_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    late_cap_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    early_cap_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    ot_max_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    late_grace_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    early_grace_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    ot_threshold_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    absent_if_no_punch: bool
    break_punch_required: bool
    break_punch_tolerance_min: int = Field(ge=0, le=MAX_RULE_MINUTES)
    absent_deduct_per_day: DecimalString = Field(ge=0, le=MAX_RULE_AMOUNT)
    late_deduct_per_occurrence: DecimalString = Field(ge=0, le=MAX_RULE_AMOUNT)
    early_deduct_per_occurrence: DecimalString = Field(ge=0, le=MAX_RULE_AMOUNT)
    missing_punch_deduct_per_occurrence: DecimalString = Field(ge=0, le=MAX_RULE_AMOUNT)


class RulePatch(WriteModel):
    """Nullable plan override fields; ``None`` inherits the company default."""

    punch_window_min: int | None = Field(default=None, ge=0, le=MAX_RULE_MINUTES)
    late_cap_min: int | None = Field(default=None, ge=0, le=MAX_RULE_MINUTES)
    early_cap_min: int | None = Field(default=None, ge=0, le=MAX_RULE_MINUTES)
    ot_max_min: int | None = Field(default=None, ge=0, le=MAX_RULE_MINUTES)
    late_grace_min: int | None = Field(default=None, ge=0, le=MAX_RULE_MINUTES)
    early_grace_min: int | None = Field(default=None, ge=0, le=MAX_RULE_MINUTES)
    ot_threshold_min: int | None = Field(default=None, ge=0, le=MAX_RULE_MINUTES)
    absent_if_no_punch: bool | None = None
    break_punch_required: bool | None = None
    break_punch_tolerance_min: int | None = Field(
        default=None, ge=0, le=MAX_RULE_MINUTES
    )
    absent_deduct_per_day: DecimalString | None = Field(
        default=None, ge=0, le=MAX_RULE_AMOUNT
    )
    late_deduct_per_occurrence: DecimalString | None = Field(
        default=None, ge=0, le=MAX_RULE_AMOUNT
    )
    early_deduct_per_occurrence: DecimalString | None = Field(
        default=None, ge=0, le=MAX_RULE_AMOUNT
    )
    missing_punch_deduct_per_occurrence: DecimalString | None = Field(
        default=None, ge=0, le=MAX_RULE_AMOUNT
    )


_RULE_FIELD_NAMES: tuple[str, ...] = (
    "punch_window_min",
    "late_cap_min",
    "early_cap_min",
    "ot_max_min",
    "late_grace_min",
    "early_grace_min",
    "ot_threshold_min",
    "absent_if_no_punch",
    "break_punch_required",
    "break_punch_tolerance_min",
    "absent_deduct_per_day",
    "late_deduct_per_occurrence",
    "early_deduct_per_occurrence",
    "missing_punch_deduct_per_occurrence",
)


# Pydantic treats a ``None`` default as "omitted", while the annotation stays
# non-nullable: the OpenAPI schema therefore advertises optional integer/bool/
# decimal fields rather than ``anyOf [<type>, null]``. An explicit ``null`` is
# still rejected by the validator below.
_OMIT: Any = None


class AttendanceRuleUpdate(WriteModel):
    """Company default rule update; omitted fields keep their current value."""

    punch_window_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    late_cap_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    early_cap_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    ot_max_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    late_grace_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    early_grace_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    ot_threshold_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    absent_if_no_punch: bool = Field(default=_OMIT)
    break_punch_required: bool = Field(default=_OMIT)
    break_punch_tolerance_min: int = Field(default=_OMIT, ge=0, le=MAX_RULE_MINUTES)
    absent_deduct_per_day: DecimalString = Field(
        default=_OMIT, ge=0, le=MAX_RULE_AMOUNT
    )
    late_deduct_per_occurrence: DecimalString = Field(
        default=_OMIT, ge=0, le=MAX_RULE_AMOUNT
    )
    early_deduct_per_occurrence: DecimalString = Field(
        default=_OMIT, ge=0, le=MAX_RULE_AMOUNT
    )
    missing_punch_deduct_per_occurrence: DecimalString = Field(
        default=_OMIT, ge=0, le=MAX_RULE_AMOUNT
    )

    @field_validator(*_RULE_FIELD_NAMES, mode="before")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class AttendanceRulePublic(ReadModel):
    id: uuid.UUID | None = None
    company_id: uuid.UUID
    is_default: bool
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
    absent_deduct_per_day: DecimalString
    late_deduct_per_occurrence: DecimalString
    early_deduct_per_occurrence: DecimalString
    missing_punch_deduct_per_occurrence: DecimalString
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ShiftCreate(WriteModel):
    company_id: uuid.UUID
    shift_code: str = Field(min_length=1, max_length=32, pattern=SHIFT_CODE_PATTERN)
    shift_name: str = Field(min_length=1, max_length=100)
    start_time: ShiftTime
    end_time: ShiftTime
    cross_day: bool = False
    break_start: ShiftTime | None = None
    break_end: ShiftTime | None = None
    rest_minutes: int = Field(default=0, ge=0)
    color: str | None = Field(default=None, max_length=16, pattern=COLOR_PATTERN)
    note: str | None = Field(default=None, max_length=500)
    is_active: bool = True

    @field_validator("shift_code", mode="before")
    @classmethod
    def _normalize_shift_code(cls, value: Any) -> Any:
        return normalize_code(value) if isinstance(value, str) else value


class ShiftUpdate(WriteModel):
    shift_name: str | None = Field(default=None, min_length=1, max_length=100)
    start_time: ShiftTime | None = None
    end_time: ShiftTime | None = None
    cross_day: bool | None = None
    break_start: ShiftTime | None = None
    break_end: ShiftTime | None = None
    rest_minutes: int | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, max_length=16, pattern=COLOR_PATTERN)
    note: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @field_validator(
        "shift_name",
        "start_time",
        "end_time",
        "cross_day",
        "rest_minutes",
        "is_active",
    )
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class ShiftPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    shift_code: str
    shift_name: str
    start_time: time
    end_time: time
    cross_day: bool
    break_start: time | None = None
    break_end: time | None = None
    rest_minutes: int
    color: str | None = None
    note: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ShiftsPublic(SQLModel):
    data: list[ShiftPublic]
    count: int


class HolidayCreate(WriteModel):
    company_id: uuid.UUID
    date: date
    name: str = Field(min_length=1, max_length=100)
    day_type: HolidayDayType
    note: str | None = Field(default=None, max_length=500)


class HolidayUpdate(WriteModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    day_type: HolidayDayType | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("name", "day_type")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class HolidayPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    date: date
    name: str
    day_type: HolidayDayType
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class HolidaysPublic(SQLModel):
    data: list[HolidayPublic]
    count: int


class HolidayCopyRequest(WriteModel):
    source_year: int = Field(ge=1900, le=9999)
    target_year: int = Field(ge=1900, le=9999)
    overwrite: bool = False


class HolidayCopyCreate(SQLModel):
    date: date
    name: str
    day_type: HolidayDayType


class HolidayCopyConflict(SQLModel):
    date: date
    name: str
    existing_name: str


class HolidayCopyPreview(SQLModel):
    create_count: int
    conflict_count: int
    creates: list[HolidayCopyCreate] = Field(default_factory=list)
    conflicts: list[HolidayCopyConflict]


class HolidayCopyResult(SQLModel):
    created: int
    updated: int
    skipped: int


class HolidaySnapshot(SQLModel):
    date: date
    name: str
    day_type: HolidayDayType


class RuleSnapshotPatch(SQLModel):
    """Read-only rule override snapshot; unknown historical fields are kept."""

    model_config = SQLModelConfig(extra="allow")

    punch_window_min: int | None = None
    late_cap_min: int | None = None
    early_cap_min: int | None = None
    ot_max_min: int | None = None
    late_grace_min: int | None = None
    early_grace_min: int | None = None
    ot_threshold_min: int | None = None
    absent_if_no_punch: bool | None = None
    break_punch_required: bool | None = None
    break_punch_tolerance_min: int | None = None
    absent_deduct_per_day: DecimalString | None = None
    late_deduct_per_occurrence: DecimalString | None = None
    early_deduct_per_occurrence: DecimalString | None = None
    missing_punch_deduct_per_occurrence: DecimalString | None = None


class PlanRuleOverrideSnapshot(SQLModel):
    plan_id: uuid.UUID
    overrides: RuleSnapshotPatch


class RulesSnapshot(SQLModel):
    company_rule: RuleValues
    plan_overrides: list[PlanRuleOverrideSnapshot]
    holidays: list[HolidaySnapshot]


class InputBatchInfo(SQLModel):
    id: uuid.UUID
    committed_at: datetime | None = None
    file_name: str | None = None
    source_rows: int | None = None
    valid_records: int | None = None


class InputBatches(SQLModel):
    punch: InputBatchInfo | None = None
    trip: InputBatchInfo | None = None
    ot: InputBatchInfo | None = None
    leave: InputBatchInfo | None = None


class CalcRunSummary(SQLModel):
    employees_total: int = 0
    employees_calculated: int = 0
    employees_skipped: int = 0
    skipped_reasons: dict[str, int] = {}
    days_total: int = 0
    days_by_status: dict[str, int] = {}
    flag_counts: dict[str, int] = {}
    late_count: int = 0
    late_minutes: int = 0
    early_count: int = 0
    early_minutes: int = 0
    missing_punch_count: int = 0
    absent_days: int = 0
    ot_weekday_minutes: int = 0
    ot_weekend_minutes: int = 0
    ot_holiday_minutes: int = 0
    comp_offset_unused_minutes: int = 0
    attendance_deduct: DecimalString = Decimal("0")


class CalcRunPublic(ReadModel):
    id: uuid.UUID
    attendance_month_id: uuid.UUID
    trigger: CalcRunTrigger
    status: CalcRunStatus
    calc_version: str
    rules_version: str
    roster_version: str
    rules_snapshot: RulesSnapshot
    input_batches: InputBatches
    summary: CalcRunSummary | None = None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime


class CalcRunsPublic(SQLModel):
    data: list[CalcRunPublic]
    count: int


class SnapshotPayload(SQLModel):
    schema_version: int = 1
    company_id: uuid.UUID
    month: MonthString
    locked_at: datetime
    locked_by: uuid.UUID
    attendance_month: dict[str, Any]
    calc_run: dict[str, Any]
    day_results: list[dict[str, Any]] = []
    shift_results: list[dict[str, Any]] = []
    month_summaries: list[dict[str, Any]] = []
    adjustments: list[dict[str, Any]] = []
    export: dict[str, Any]


class AttendanceMonthSnapshotPublic(ReadModel):
    id: uuid.UUID
    version: int
    locked_at: datetime
    locked_by: uuid.UUID
    locked_by_name: str | None = None
    calc_run_id: uuid.UUID
    summary: CalcRunSummary | None = None
    payload: SnapshotPayload | None = None


class AttendanceMonthSnapshotsPublic(SQLModel):
    data: list[AttendanceMonthSnapshotPublic]
    count: int


class MonthCounts(SQLModel):
    employee_count: int = 0
    day_result_count: int = 0
    abnormal_day_count: int = 0
    month_summary_count: int = 0


class AttendanceMonthPublic(ReadModel):
    id: uuid.UUID | None = None
    exists: bool
    company_id: uuid.UUID
    month: MonthString
    status: AttendanceMonthStatus
    is_stale: bool
    calculated_at: datetime | None = None
    confirmed_at: datetime | None = None
    locked_at: datetime | None = None
    unlock_reason: str | None = None
    latest_calc_run: CalcRunPublic | None = None
    active_batches: InputBatches
    counts: MonthCounts
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AttendanceMonthsPublic(SQLModel):
    data: list[AttendanceMonthPublic]
    count: int
