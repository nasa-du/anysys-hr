"""Scheduling schemas: plans, scopes, days, overrides, and roster entries."""

import uuid
from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import Field, field_validator
from sqlmodel import SQLModel

from app.enums import (
    DayType,
    PlanStatus,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.schemas_attendance.common import (
    EmployeeDisplay,
    MonthString,
    ReadModel,
    WriteModel,
)
from app.schemas_attendance.core import RulePatch, RuleValues


class PlanScopePublic(SQLModel):
    id: uuid.UUID
    scope_id: uuid.UUID
    scope_code: str | None = None
    scope_name: str | None = None


class PlanDayInput(WriteModel):
    day_of_month: int = Field(ge=1, le=31)
    seq: int = Field(ge=0)
    shift_id: uuid.UUID


class PlanDayPublic(ReadModel):
    id: uuid.UUID
    day_of_month: int
    seq: int
    shift_id: uuid.UUID
    shift_code: str | None = None
    shift_name: str | None = None
    shift_color: str | None = None
    shift_is_active: bool | None = None


class SchedulePlanCreate(WriteModel):
    company_id: uuid.UUID
    month: MonthString
    plan_name: str = Field(min_length=1, max_length=100)
    scope_type: ScheduleScopeType
    scope_ids: list[uuid.UUID] = Field(default_factory=list)
    days: list[PlanDayInput] = Field(default_factory=list)
    rule_overrides: RulePatch | None = None
    note: str | None = Field(default=None, max_length=500)


class SchedulePlanUpdate(WriteModel):
    plan_name: str | None = Field(default=None, min_length=1, max_length=100)
    scope_type: ScheduleScopeType | None = None
    scope_ids: list[uuid.UUID] | None = None
    days: list[PlanDayInput] | None = None
    rule_overrides: RulePatch | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("plan_name", "scope_type", "scope_ids", "days")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class SchedulePlanPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    month: MonthString
    plan_name: str
    scope_type: ScheduleScopeType
    status: PlanStatus
    copied_from_plan_id: uuid.UUID | None = None
    note: str | None = None
    scopes: list[PlanScopePublic] = Field(default_factory=list)
    days: list[PlanDayPublic] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SchedulePlansPublic(SQLModel):
    data: list[SchedulePlanPublic]
    count: int


class SchedulePlanPreviewRequest(WriteModel):
    company_id: uuid.UUID
    month: MonthString
    plan_id: uuid.UUID | None = None
    scope_type: ScheduleScopeType
    scope_ids: list[uuid.UUID] = Field(default_factory=list)
    days: list[PlanDayInput] = Field(default_factory=list)


class SchedulePlanConflict(SQLModel):
    scope_type: ScheduleScopeType
    scope_id: uuid.UUID
    plan_id: uuid.UUID
    plan_name: str


class SchedulePlanPreview(SQLModel):
    can_apply: bool
    affected_employees: int
    added: int
    updated: int
    deleted: int
    manual_preserved: int
    conflicts: list[SchedulePlanConflict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RosterChangeSummary(SQLModel):
    added: int = 0
    updated: int = 0
    deleted: int = 0
    manual_preserved: int = 0


class SchedulePlanMutationPublic(SQLModel):
    plan: SchedulePlanPublic
    roster_change: RosterChangeSummary
    month_stale: bool


class PlanCopyRequest(WriteModel):
    target_month: MonthString
    include_manual_exceptions: bool = False
    confirm_overwrite: bool = False


class PlanCopyPreview(SQLModel):
    target_month: MonthString
    can_apply: bool
    added: int
    updated: int
    deleted: int
    manual_preserved: int
    conflicts: list[SchedulePlanConflict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PlanRuleOverridesUpdate(WriteModel):
    overrides: RulePatch = Field(default_factory=RulePatch)


class PlanRuleOverridesPublic(SQLModel):
    overrides: RulePatch
    effective: RuleValues
    company_default: RuleValues


class RosterShiftInput(WriteModel):
    seq: int = Field(ge=0)
    shift_id: uuid.UUID


class RosterEntryCreate(WriteModel):
    employee_id: uuid.UUID
    work_date: date
    state: RosterState
    shifts: list[RosterShiftInput] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=500)


class RosterEntryUpdate(WriteModel):
    state: RosterState | None = None
    shifts: list[RosterShiftInput] | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("state", "shifts")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class RosterEntryShiftPublic(ReadModel):
    id: uuid.UUID
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


class RosterEntryPublic(ReadModel):
    id: uuid.UUID
    company_id: uuid.UUID
    employee_id: uuid.UUID
    employee_no: str | None = None
    employee_name: str | None = None
    department_name: str | None = None
    work_date: date
    state: RosterState
    source: RosterSource
    plan_id: uuid.UUID | None = None
    note: str | None = None
    shifts: list[RosterEntryShiftPublic] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RosterEntriesPublic(SQLModel):
    data: list[RosterEntryPublic]
    count: int


class RosterCalendarDay(SQLModel):
    work_date: date
    day_type: DayType
    state: Literal["work", "rest", "unscheduled"]
    source: RosterSource | None = None
    plan_id: uuid.UUID | None = None
    shifts: list[RosterEntryShiftPublic] = Field(default_factory=list)
    note: str | None = None


class EmployeeRosterCalendarPublic(SQLModel):
    employee: EmployeeDisplay
    month: MonthString
    days: list[RosterCalendarDay]


class RosterDayEmployee(SQLModel):
    employee: EmployeeDisplay
    state: Literal["work", "rest"]
    source: RosterSource
    plan_id: uuid.UUID | None = None
    shifts: list[RosterEntryShiftPublic] = Field(default_factory=list)
    note: str | None = None


class RosterDayPublic(SQLModel):
    date: date
    employees: list[RosterDayEmployee]
    unscheduled_count: int


class ShiftCountPublic(SQLModel):
    shift_id: uuid.UUID
    shift_code: str
    shift_name: str
    color: str | None = None
    count: int


class RosterMonthDayPublic(SQLModel):
    date: date
    day_type: DayType
    work_count: int
    rest_count: int
    unscheduled_count: int
    manual_count: int
    shift_counts: list[ShiftCountPublic] = Field(default_factory=list)


class RosterMonthPlanPublic(SQLModel):
    id: uuid.UUID
    plan_name: str
    scope_type: ScheduleScopeType
    status: PlanStatus


class RosterMonthPublic(SQLModel):
    month: MonthString
    days: list[RosterMonthDayPublic]
    plans: list[RosterMonthPlanPublic]


class RosterEmployeeSummaryPublic(EmployeeDisplay):
    work_days: int
    rest_days: int
    unscheduled_days: int
    manual_exception_count: int


class RosterEmployeeSummariesPublic(SQLModel):
    data: list[RosterEmployeeSummaryPublic]
    count: int


class PersonnelSyncPreview(SQLModel):
    added: int
    removed: int
    changed: int
    entries_added: int
    entries_updated: int
    entries_deleted: int
    manual_preserved: int


class PersonnelSyncRequest(WriteModel):
    company_id: uuid.UUID
    month: MonthString


class PersonnelSyncResult(SQLModel):
    added: int
    removed: int
    changed: int
    entries_added: int
    entries_updated: int
    entries_deleted: int
    manual_preserved: int
    month_stale: bool


class RosterEntryUpsert(WriteModel):
    entry_id: uuid.UUID | None = None
    employee_id: uuid.UUID
    work_date: date
    state: RosterState
    shifts: list[RosterShiftInput] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=500)


class RosterEntryBatchRequest(WriteModel):
    company_id: uuid.UUID
    entries: list[RosterEntryUpsert] = Field(default_factory=list)
    delete_entry_ids: list[uuid.UUID] = Field(default_factory=list)


class RosterEntryBatchResult(SQLModel):
    created: int
    updated: int
    deleted: int
    month_stale: bool
