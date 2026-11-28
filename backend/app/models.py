import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from pydantic import EmailStr
from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.enums import (
    AdjustmentStatus,
    AttendanceMonthStatus,
    CalcRunStatus,
    CalcRunTrigger,
    ContractType,
    DayStatus,
    DayType,
    EmployeeStatus,
    Gender,
    HolidayDayType,
    ImportBatchStatus,
    ImportDataType,
    ImportSeverity,
    ImportSource,
    LeaveKind,
    PayrollCalcRunStatus,
    PayrollCalcRunTrigger,
    PayrollConfigEntityType,
    PayrollExportStatus,
    PayrollExportType,
    PayrollGlobalParamType,
    PayrollImportBatchSource,
    PayrollImportBatchStatus,
    PayrollImportRowStatus,
    PayrollInputSource,
    PayrollMonthEventType,
    PayrollMonthStatus,
    PayrollResultSource,
    PlanStatus,
    ResultRosterState,
    RosterSource,
    RosterState,
    SalaryFieldCalcMode,
    SalaryFieldCategory,
    ScheduleScopeType,
    TripKind,
)


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_column(*constraints: Any, nullable: bool) -> Column[Any]:
    return Column(sa.UUID(as_uuid=True), *constraints, nullable=nullable)


def _enum_column(
    enum_type: type[StrEnum],
    constraint_name: str,
    *,
    nullable: bool,
    length: int | None = None,
) -> Column[Any]:
    return Column(
        SAEnum(
            enum_type,
            native_enum=False,
            create_constraint=True,
            name=constraint_name,
            length=length,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=nullable,
    )


def _jsonb_column(*, nullable: bool, default: Any = None) -> Column[Any]:
    kwargs: dict[str, Any] = {"nullable": nullable}
    if default is not None:
        kwargs["default"] = default
    # ``none_as_null`` persists Python ``None`` as SQL NULL instead of JSON
    # ``null``, so retention and cleanup predicates can use ``IS NULL``.
    return Column(JSONB(none_as_null=True), **kwargs)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(default_factory=get_datetime_utc)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# Basic Management models. These are table-only: display fields and query
# composition belong to the service layer, not to ORM relationships.


class Company(SQLModel, table=True):
    __tablename__ = "company"
    __table_args__ = (UniqueConstraint("company_code", name="uq_company_company_code"),)

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_code: str = Field(max_length=32)
    company_name: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class Department(SQLModel, table=True):
    __tablename__ = "department"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "dept_code", name="uq_department_company_dept_code"
        ),
        Index("ix_department_company_id", "company_id"),
        Index("ix_department_parent_id", "parent_id"),
        Index("ix_department_manager_id", "manager_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    dept_code: str = Field(max_length=32)
    dept_name: str = Field(max_length=100)
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_department_company_id_company",
            ),
            nullable=False,
        )
    )
    parent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "department.id",
                ondelete="RESTRICT",
                name="fk_department_parent_id_department",
            ),
            nullable=True,
        ),
    )
    manager_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="SET NULL",
                name="fk_department_manager_id_employee",
            ),
            nullable=True,
        ),
    )
    order_no: int = Field(default=0)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class Position(SQLModel, table=True):
    __tablename__ = "position"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "position_code",
            name="uq_position_company_position_code",
        ),
        Index("ix_position_company_id", "company_id"),
        Index("ix_position_dept_id", "dept_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    position_code: str = Field(max_length=32)
    position_name: str = Field(max_length=100)
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_position_company_id_company",
            ),
            nullable=False,
        )
    )
    dept_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "department.id",
                ondelete="SET NULL",
                name="fk_position_dept_id_department",
            ),
            nullable=True,
        ),
    )
    order_no: int = Field(default=0)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class CostCenter(SQLModel, table=True):
    __tablename__ = "cost_center"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "cost_org_code",
            name="uq_cost_center_company_cost_org_code",
        ),
        Index("ix_cost_center_company_id", "company_id"),
        Index("ix_cost_center_parent_id", "parent_id"),
        Index("ix_cost_center_manager_id", "manager_id"),
        sa.CheckConstraint("budget >= 0", name="ck_cost_center_budget_non_negative"),
        sa.CheckConstraint(
            "warn_pct BETWEEN 1 AND 100", name="ck_cost_center_warn_pct_range"
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    cost_org_code: str = Field(max_length=32)
    cost_org_name: str = Field(max_length=100)
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_cost_center_company_id_company",
            ),
            nullable=False,
        )
    )
    parent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "cost_center.id",
                ondelete="RESTRICT",
                name="fk_cost_center_parent_id_cost_center",
            ),
            nullable=True,
        ),
    )
    manager_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="SET NULL",
                name="fk_cost_center_manager_id_employee",
            ),
            nullable=True,
        ),
    )
    budget: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    warn_pct: int = Field(default=85)
    order_no: int = Field(default=0)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class Employee(SQLModel, table=True):
    __tablename__ = "employee"
    __table_args__ = (
        UniqueConstraint("employee_no", name="uq_employee_employee_no"),
        Index("ix_employee_dept_id", "dept_id"),
        Index("ix_employee_position_id", "position_id"),
        Index("ix_employee_cost_org_id", "cost_org_id"),
        Index("ix_employee_manager_id", "manager_id"),
        Index("ix_employee_status", "status"),
        sa.CheckConstraint(
            "daily_hours IS NULL OR (daily_hours > 0 AND daily_hours <= 24)",
            name="ck_employee_daily_hours_range",
        ),
        sa.CheckConstraint(
            "monthly_rest IS NULL OR monthly_rest >= 0",
            name="ck_employee_monthly_rest_non_negative",
        ),
        sa.CheckConstraint(
            "confidentiality_level IS NULL OR confidentiality_level BETWEEN 1 AND 5",
            name="ck_employee_confidentiality_level_range",
        ),
        sa.CheckConstraint(
            "resign_date IS NULL OR resign_date >= hire_date",
            name="ck_employee_resign_date_after_hire",
        ),
        sa.CheckConstraint(
            "(status = 'resigned') = (resign_date IS NOT NULL)",
            name="ck_employee_resigned_date_required",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    employee_no: str = Field(max_length=32)
    name: str = Field(max_length=100)
    gender: Gender | None = Field(
        default=None,
        sa_column=_enum_column(Gender, "ck_employee_gender", nullable=True),
    )
    dept_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "department.id",
                ondelete="RESTRICT",
                name="fk_employee_dept_id_department",
            ),
            nullable=False,
        )
    )
    position_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "position.id",
                ondelete="RESTRICT",
                name="fk_employee_position_id_position",
            ),
            nullable=False,
        )
    )
    cost_org_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "cost_center.id",
                ondelete="RESTRICT",
                name="fk_employee_cost_org_id_cost_center",
            ),
            nullable=True,
        ),
    )
    manager_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="SET NULL",
                name="fk_employee_manager_id_employee",
            ),
            nullable=True,
        ),
    )
    status: EmployeeStatus = Field(
        default=EmployeeStatus.ACTIVE,
        sa_column=_enum_column(EmployeeStatus, "ck_employee_status", nullable=False),
    )
    hire_date: date
    resign_date: date | None = None
    contract_type: ContractType = Field(
        sa_column=_enum_column(
            ContractType, "ck_employee_contract_type", nullable=False
        )
    )
    daily_hours: Decimal | None = Field(default=None, max_digits=4, decimal_places=2)
    monthly_rest: int | None = None
    confidentiality_level: int | None = None
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


# Attendance models. These are table-only: every relationship is expressed by
# an explicit foreign-key column and the service layer composes queries.
#
# All primary keys are UUID v7 generated in Python, enum columns are VARCHAR +
# CHECK via non-native ``SAEnum``, and timestamps are TIMESTAMPTZ generated in
# Python. Migrations are the contract; see docs/specs/attendance-management.md
# sections 4 and 12.

ATTENDANCE_TABLES: tuple[str, ...] = (
    "shift",
    "holiday",
    "attendance_rule",
    "attendance_month",
    "calc_run",
    "attendance_month_snapshot",
    "schedule_plan",
    "plan_scope",
    "plan_day",
    "plan_rule_override",
    "roster_entry",
    "roster_entry_shift",
    "import_batch",
    "import_batch_error",
    "import_mapping_template",
    "punch_record",
    "oa_trip",
    "oa_overtime",
    "oa_overtime_day",
    "oa_leave",
    "attendance_day_result",
    "attendance_day_shift_result",
    "attendance_month_summary",
    "attendance_result_adjustment",
)

_RULE_INT_FIELDS: tuple[str, ...] = (
    "punch_window_min",
    "late_cap_min",
    "early_cap_min",
    "ot_max_min",
    "late_grace_min",
    "early_grace_min",
    "ot_threshold_min",
    "break_punch_tolerance_min",
)
_RULE_DECIMAL_FIELDS: tuple[str, ...] = (
    "absent_deduct_per_day",
    "late_deduct_per_occurrence",
    "early_deduct_per_occurrence",
    "missing_punch_deduct_per_occurrence",
)
# PostgreSQL identifiers are limited to 63 bytes; abbreviate only the field
# whose full name would overflow the limit.
_RULE_CHECK_FIELD_NAMES: dict[str, str] = {
    "missing_punch_deduct_per_occurrence": "missing_punch_deduct_per_occ",
}


def _rule_check_name(prefix: str, field: str) -> str:
    return f"{prefix}_{_RULE_CHECK_FIELD_NAMES.get(field, field)}_non_negative"


def _positive_rule_checks(prefix: str) -> tuple[sa.CheckConstraint, ...]:
    return tuple(
        sa.CheckConstraint(f"{field} >= 0", name=_rule_check_name(prefix, field))
        for field in (*_RULE_INT_FIELDS, *_RULE_DECIMAL_FIELDS)
    )


def _nullable_positive_rule_checks(prefix: str) -> tuple[sa.CheckConstraint, ...]:
    return tuple(
        sa.CheckConstraint(
            f"{field} IS NULL OR {field} >= 0",
            name=_rule_check_name(prefix, field),
        )
        for field in (*_RULE_INT_FIELDS, *_RULE_DECIMAL_FIELDS)
    )


class Shift(SQLModel, table=True):
    __tablename__ = "shift"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "shift_code", name="uq_shift_company_shift_code"
        ),
        sa.CheckConstraint(
            "(cross_day AND end_time <= start_time) "
            "OR (NOT cross_day AND end_time > start_time)",
            name="ck_shift_cross_day",
        ),
        sa.CheckConstraint(
            "(break_start IS NULL) = (break_end IS NULL)",
            name="ck_shift_break_pair",
        ),
        sa.CheckConstraint("rest_minutes >= 0", name="ck_shift_rest_minutes"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_shift_company_id_company",
            ),
            nullable=False,
        )
    )
    shift_code: str = Field(max_length=32)
    shift_name: str = Field(max_length=100)
    start_time: time
    end_time: time
    cross_day: bool = Field(default=False)
    break_start: time | None = Field(default=None)
    break_end: time | None = Field(default=None)
    rest_minutes: int = Field(default=0)
    color: str | None = Field(default=None, max_length=16)
    note: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class Holiday(SQLModel, table=True):
    __tablename__ = "holiday"
    __table_args__ = (
        UniqueConstraint("company_id", "date", name="uq_holiday_company_date"),
        Index("ix_holiday_company_date", "company_id", "date"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_holiday_company_id_company",
            ),
            nullable=False,
        )
    )
    date: date
    name: str = Field(max_length=100)
    day_type: HolidayDayType = Field(
        sa_column=_enum_column(HolidayDayType, "ck_holiday_day_type", nullable=False)
    )
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class AttendanceRule(SQLModel, table=True):
    __tablename__ = "attendance_rule"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_attendance_rule_company"),
        *_positive_rule_checks("ck_attendance_rule"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_attendance_rule_company_id_company",
            ),
            nullable=False,
        )
    )
    punch_window_min: int = Field(default=120)
    late_cap_min: int = Field(default=240)
    early_cap_min: int = Field(default=240)
    ot_max_min: int = Field(default=600)
    late_grace_min: int = Field(default=5)
    early_grace_min: int = Field(default=5)
    ot_threshold_min: int = Field(default=30)
    absent_if_no_punch: bool = Field(default=True)
    break_punch_required: bool = Field(default=True)
    break_punch_tolerance_min: int = Field(default=60)
    absent_deduct_per_day: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    late_deduct_per_occurrence: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    early_deduct_per_occurrence: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    missing_punch_deduct_per_occurrence: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class AttendanceMonth(SQLModel, table=True):
    __tablename__ = "attendance_month"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "month", name="uq_attendance_month_company_month"
        ),
        Index("ix_attendance_month_company_status", "company_id", "status"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_attendance_month_company_id_company",
            ),
            nullable=False,
        )
    )
    month: date
    status: AttendanceMonthStatus = Field(
        default=AttendanceMonthStatus.DRAFT,
        sa_column=_enum_column(
            AttendanceMonthStatus, "ck_attendance_month_status", nullable=False
        ),
    )
    is_stale: bool = Field(default=True)
    calculated_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    confirmed_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    locked_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    unlock_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class CalcRun(SQLModel, table=True):
    __tablename__ = "calc_run"
    __table_args__ = (
        Index("ix_calc_run_month_started", "attendance_month_id", "started_at"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    attendance_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "attendance_month.id",
                ondelete="CASCADE",
                name="fk_calc_run_attendance_month_id_attendance_month",
            ),
            nullable=False,
        )
    )
    trigger: CalcRunTrigger = Field(
        sa_column=_enum_column(CalcRunTrigger, "ck_calc_run_trigger", nullable=False)
    )
    status: CalcRunStatus = Field(
        sa_column=_enum_column(CalcRunStatus, "ck_calc_run_status", nullable=False)
    )
    calc_version: str = Field(max_length=32)
    rules_version: str = Field(max_length=64)
    roster_version: str = Field(max_length=64)
    rules_snapshot: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    input_batches: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    summary: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    error_code: str | None = Field(default=None, max_length=50)
    error_message: str | None = Field(default=None, max_length=500)
    started_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    finished_at: datetime = Field(sa_type=sa.DateTime(timezone=True))


class AttendanceMonthSnapshot(SQLModel, table=True):
    __tablename__ = "attendance_month_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "attendance_month_id",
            "version",
            name="uq_attendance_month_snapshot_month_version",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    attendance_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "attendance_month.id",
                ondelete="CASCADE",
                name="fk_attendance_month_snapshot_month_id_attendance_month",
            ),
            nullable=False,
        )
    )
    calc_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_run.id",
                ondelete="RESTRICT",
                name="fk_attendance_month_snapshot_calc_run_id_calc_run",
            ),
            nullable=False,
        )
    )
    version: int
    locked_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    locked_by: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_attendance_month_snapshot_locked_by_user",
            ),
            nullable=False,
        )
    )
    payload: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))


class SchedulePlan(SQLModel, table=True):
    __tablename__ = "schedule_plan"
    __table_args__ = (
        Index(
            "ix_schedule_plan_company_month_status",
            "company_id",
            "month",
            "status",
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1",
            name="ck_schedule_plan_month_first_day",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_schedule_plan_company_id_company",
            ),
            nullable=False,
        )
    )
    month: date
    plan_name: str = Field(max_length=100)
    scope_type: ScheduleScopeType = Field(
        sa_column=_enum_column(
            ScheduleScopeType, "ck_schedule_plan_scope_type", nullable=False
        )
    )
    status: PlanStatus = Field(
        default=PlanStatus.ENABLED,
        sa_column=_enum_column(PlanStatus, "ck_schedule_plan_status", nullable=False),
    )
    copied_from_plan_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "schedule_plan.id",
                ondelete="SET NULL",
                name="fk_schedule_plan_copied_from_plan_id_schedule_plan",
            ),
            nullable=True,
        ),
    )
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PlanScope(SQLModel, table=True):
    __tablename__ = "plan_scope"
    __table_args__ = (
        UniqueConstraint("plan_id", "scope_id", name="uq_plan_scope_plan_scope_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    plan_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "schedule_plan.id",
                ondelete="CASCADE",
                name="fk_plan_scope_plan_id_schedule_plan",
            ),
            nullable=False,
        )
    )
    scope_id: uuid.UUID = Field(sa_type=sa.UUID(as_uuid=True))


class PlanDay(SQLModel, table=True):
    __tablename__ = "plan_day"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "day_of_month",
            "seq",
            name="uq_plan_day_plan_day_seq",
        ),
        UniqueConstraint(
            "plan_id",
            "day_of_month",
            "shift_id",
            name="uq_plan_day_plan_day_shift",
        ),
        sa.CheckConstraint(
            "day_of_month BETWEEN 1 AND 31",
            name="ck_plan_day_day_of_month_range",
        ),
        sa.CheckConstraint("seq >= 0", name="ck_plan_day_seq_non_negative"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    plan_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "schedule_plan.id",
                ondelete="CASCADE",
                name="fk_plan_day_plan_id_schedule_plan",
            ),
            nullable=False,
        )
    )
    day_of_month: int
    seq: int
    shift_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "shift.id",
                ondelete="RESTRICT",
                name="fk_plan_day_shift_id_shift",
            ),
            nullable=False,
        )
    )


class PlanRuleOverride(SQLModel, table=True):
    __tablename__ = "plan_rule_override"
    __table_args__ = (*_nullable_positive_rule_checks("ck_plan_rule_override"),)

    plan_id: uuid.UUID = Field(
        sa_column=Column(
            sa.UUID(as_uuid=True),
            ForeignKey(
                "schedule_plan.id",
                ondelete="CASCADE",
                name="fk_plan_rule_override_plan_id_schedule_plan",
            ),
            primary_key=True,
            nullable=False,
        )
    )
    punch_window_min: int | None = Field(default=None)
    late_cap_min: int | None = Field(default=None)
    early_cap_min: int | None = Field(default=None)
    ot_max_min: int | None = Field(default=None)
    late_grace_min: int | None = Field(default=None)
    early_grace_min: int | None = Field(default=None)
    ot_threshold_min: int | None = Field(default=None)
    absent_if_no_punch: bool | None = Field(default=None)
    break_punch_required: bool | None = Field(default=None)
    break_punch_tolerance_min: int | None = Field(default=None)
    absent_deduct_per_day: Decimal | None = Field(
        default=None, max_digits=14, decimal_places=2
    )
    late_deduct_per_occurrence: Decimal | None = Field(
        default=None, max_digits=14, decimal_places=2
    )
    early_deduct_per_occurrence: Decimal | None = Field(
        default=None, max_digits=14, decimal_places=2
    )
    missing_punch_deduct_per_occurrence: Decimal | None = Field(
        default=None, max_digits=14, decimal_places=2
    )


class RosterEntry(SQLModel, table=True):
    __tablename__ = "roster_entry"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "work_date", name="uq_roster_entry_employee_date"
        ),
        Index("ix_roster_entry_company_date", "company_id", "work_date"),
        Index("ix_roster_entry_employee_date", "employee_id", "work_date"),
        Index("ix_roster_entry_plan_id", "plan_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_roster_entry_company_id_company",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_roster_entry_employee_id_employee",
            ),
            nullable=False,
        )
    )
    work_date: date
    state: RosterState = Field(
        sa_column=_enum_column(RosterState, "ck_roster_entry_state", nullable=False)
    )
    source: RosterSource = Field(
        sa_column=_enum_column(RosterSource, "ck_roster_entry_source", nullable=False)
    )
    plan_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "schedule_plan.id",
                ondelete="SET NULL",
                name="fk_roster_entry_plan_id_schedule_plan",
            ),
            nullable=True,
        ),
    )
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class RosterEntryShift(SQLModel, table=True):
    __tablename__ = "roster_entry_shift"
    __table_args__ = (
        UniqueConstraint(
            "roster_entry_id", "seq", name="uq_roster_entry_shift_entry_seq"
        ),
        sa.CheckConstraint("seq >= 0", name="ck_roster_entry_shift_seq_non_negative"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    roster_entry_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "roster_entry.id",
                ondelete="CASCADE",
                name="fk_roster_entry_shift_roster_entry_id_roster_entry",
            ),
            nullable=False,
        )
    )
    seq: int
    shift_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "shift.id",
                ondelete="RESTRICT",
                name="fk_roster_entry_shift_shift_id_shift",
            ),
            nullable=False,
        )
    )
    shift_code: str = Field(max_length=32)
    shift_name: str = Field(max_length=100)
    start_time: time
    end_time: time
    cross_day: bool
    break_start: time | None = Field(default=None)
    break_end: time | None = Field(default=None)
    rest_minutes: int


class ImportBatch(SQLModel, table=True):
    __tablename__ = "import_batch"
    __table_args__ = (
        Index(
            "ix_import_batch_company_type_month_status",
            "company_id",
            "data_type",
            "month",
            "status",
        ),
        Index("ix_import_batch_expires_at", "expires_at"),
        Index(
            "uq_import_batch_company_type_month_committed",
            "company_id",
            "data_type",
            "month",
            unique=True,
            postgresql_where=sa.text("status = 'committed'"),
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1",
            name="ck_import_batch_month_first_day",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_import_batch_company_id_company",
            ),
            nullable=False,
        )
    )
    data_type: ImportDataType = Field(
        sa_column=_enum_column(
            ImportDataType, "ck_import_batch_data_type", nullable=False
        )
    )
    month: date
    status: ImportBatchStatus = Field(
        sa_column=_enum_column(
            ImportBatchStatus, "ck_import_batch_status", nullable=False
        )
    )
    source: ImportSource = Field(
        sa_column=_enum_column(ImportSource, "ck_import_batch_source", nullable=False)
    )
    file_name: str | None = Field(default=None, max_length=255)
    file_size: int | None = Field(default=None)
    file_sha256: str | None = Field(default=None, max_length=64)
    sheet_name: str | None = Field(default=None, max_length=100)
    header_row_number: int | None = Field(default=None)
    header_columns: list[Any] = Field(sa_column=_jsonb_column(nullable=False))
    column_mapping: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    parser_version: str = Field(max_length=32)
    source_rows: int = Field(default=0)
    valid_records: int = Field(default=0)
    skipped_records: int = Field(default=0)
    error_records: int = Field(default=0)
    warning_records: int = Field(default=0)
    skip_counts: dict[str, Any] = Field(
        sa_column=_jsonb_column(nullable=False, default=dict)
    )
    warning_counts: dict[str, Any] = Field(
        sa_column=_jsonb_column(nullable=False, default=dict)
    )
    operator_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_import_batch_operator_id_user",
            ),
            nullable=False,
        )
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    committed_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    superseded_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    discarded_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    revoked_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    expires_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    superseded_by_batch_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "import_batch.id",
                ondelete="SET NULL",
                name="fk_import_batch_superseded_by_batch_id_import_batch",
            ),
            nullable=True,
        ),
    )
    discard_reason: str | None = Field(default=None, max_length=32)


class ImportBatchError(SQLModel, table=True):
    __tablename__ = "import_batch_error"
    __table_args__ = (
        Index("ix_import_batch_error_batch_severity", "batch_id", "severity"),
        Index("ix_import_batch_error_batch_row", "batch_id", "source_row_number"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    batch_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "import_batch.id",
                ondelete="CASCADE",
                name="fk_import_batch_error_batch_id_import_batch",
            ),
            nullable=False,
        )
    )
    source_row_number: int
    column_name: str | None = Field(default=None, max_length=100)
    code: str = Field(max_length=50)
    message: str = Field(max_length=500)
    severity: ImportSeverity = Field(
        sa_column=_enum_column(
            ImportSeverity, "ck_import_batch_error_severity", nullable=False
        )
    )
    raw_row: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class ImportMappingTemplate(SQLModel, table=True):
    __tablename__ = "import_mapping_template"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "data_type",
            name="uq_import_mapping_template_company_type",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_import_mapping_template_company_id_company",
            ),
            nullable=False,
        )
    )
    data_type: ImportDataType = Field(
        sa_column=_enum_column(
            ImportDataType, "ck_import_mapping_template_data_type", nullable=False
        )
    )
    mapping: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    header_columns: list[Any] = Field(sa_column=_jsonb_column(nullable=False))
    updated_by: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_import_mapping_template_updated_by_user",
            ),
            nullable=False,
        )
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PunchRecord(SQLModel, table=True):
    __tablename__ = "punch_record"
    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "employee_id",
            "attendance_date",
            "punch_time",
            name="uq_punch_record_batch_employee_date_time",
        ),
        UniqueConstraint(
            "batch_id", "source_row_number", name="uq_punch_record_batch_row"
        ),
        Index(
            "ix_punch_record_company_employee_date",
            "company_id",
            "employee_id",
            "attendance_date",
        ),
        Index("ix_punch_record_company_date", "company_id", "attendance_date"),
        Index("ix_punch_record_batch_id", "batch_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_punch_record_company_id_company",
            ),
            nullable=False,
        )
    )
    batch_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "import_batch.id",
                ondelete="CASCADE",
                name="fk_punch_record_batch_id_import_batch",
            ),
            nullable=False,
        )
    )
    source_row_number: int
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_punch_record_employee_id_employee",
            ),
            nullable=False,
        )
    )
    employee_no_raw: str = Field(max_length=32)
    employee_name_raw: str = Field(max_length=100)
    department_raw: str = Field(max_length=100)
    attendance_date: date
    punch_time: datetime = Field(sa_type=sa.DateTime(timezone=True))
    punch_result_raw: str = Field(max_length=50)
    device_raw: str | None = Field(default=None, max_length=200)
    address_raw: str | None = Field(default=None, max_length=200)
    raw_row: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class OaTrip(SQLModel, table=True):
    __tablename__ = "oa_trip"
    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "source_row_number",
            "split_index",
            name="uq_oa_trip_batch_row_split",
        ),
        Index(
            "uq_oa_trip_batch_approval_employee",
            "batch_id",
            "approval_no",
            "employee_id",
            unique=True,
            postgresql_where=sa.text("approval_no IS NOT NULL"),
        ),
        Index(
            "ix_oa_trip_company_dates",
            "company_id",
            "start_date",
            "end_date",
        ),
        Index("ix_oa_trip_batch_id", "batch_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_oa_trip_company_id_company",
            ),
            nullable=False,
        )
    )
    batch_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "import_batch.id",
                ondelete="CASCADE",
                name="fk_oa_trip_batch_id_import_batch",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_oa_trip_employee_id_employee",
            ),
            nullable=False,
        )
    )
    source_row_number: int
    split_index: int = Field(default=0)
    approval_no: str | None = Field(default=None, max_length=100)
    employee_name_raw: str = Field(max_length=100)
    department_raw: str = Field(max_length=100)
    application_type_raw: str | None = Field(default=None, max_length=100)
    approval_result_raw: str = Field(max_length=50)
    approval_status_raw: str = Field(max_length=50)
    start_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    end_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    start_date: date
    end_date: date
    days_declared: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)
    reason: str | None = Field(default=None, max_length=500)
    raw_row: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class OaOvertime(SQLModel, table=True):
    __tablename__ = "oa_overtime"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "source_row_number", name="uq_oa_overtime_batch_row"
        ),
        Index(
            "uq_oa_overtime_batch_approval_employee",
            "batch_id",
            "approval_no",
            "employee_id",
            unique=True,
            postgresql_where=sa.text("approval_no IS NOT NULL"),
        ),
        Index(
            "ix_oa_overtime_company_range",
            "company_id",
            "start_at",
            "end_at",
        ),
        Index("ix_oa_overtime_batch_id", "batch_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_oa_overtime_company_id_company",
            ),
            nullable=False,
        )
    )
    batch_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "import_batch.id",
                ondelete="CASCADE",
                name="fk_oa_overtime_batch_id_import_batch",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_oa_overtime_employee_id_employee",
            ),
            nullable=False,
        )
    )
    source_row_number: int
    approval_no: str | None = Field(default=None, max_length=100)
    employee_name_raw: str = Field(max_length=100)
    department_raw: str = Field(max_length=100)
    approval_result_raw: str = Field(max_length=50)
    approval_status_raw: str = Field(max_length=50)
    start_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    end_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    declared_raw: str | None = Field(default=None, max_length=50)
    reason: str | None = Field(default=None, max_length=500)
    raw_row: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class OaOvertimeDay(SQLModel, table=True):
    __tablename__ = "oa_overtime_day"
    __table_args__ = (
        UniqueConstraint(
            "overtime_id",
            "work_date",
            name="uq_oa_overtime_day_overtime_date",
        ),
        Index("ix_oa_overtime_day_company_date", "company_id", "work_date"),
        Index("ix_oa_overtime_day_overtime_id", "overtime_id"),
        sa.CheckConstraint(
            "minutes BETWEEN 0 AND 480",
            name="ck_oa_overtime_day_minutes_range",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_oa_overtime_day_company_id_company",
            ),
            nullable=False,
        )
    )
    overtime_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "oa_overtime.id",
                ondelete="CASCADE",
                name="fk_oa_overtime_day_overtime_id_oa_overtime",
            ),
            nullable=False,
        )
    )
    work_date: date
    minutes: int
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class OaLeave(SQLModel, table=True):
    __tablename__ = "oa_leave"
    __table_args__ = (
        UniqueConstraint("batch_id", "source_row_number", name="uq_oa_leave_batch_row"),
        Index(
            "uq_oa_leave_batch_approval_employee",
            "batch_id",
            "approval_no",
            "employee_id",
            unique=True,
            postgresql_where=sa.text("approval_no IS NOT NULL"),
        ),
        Index(
            "ix_oa_leave_company_dates",
            "company_id",
            "rest_start_date",
            "rest_end_date",
        ),
        Index("ix_oa_leave_batch_id", "batch_id"),
        sa.CheckConstraint("days > 0", name="ck_oa_leave_days_positive"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_oa_leave_company_id_company",
            ),
            nullable=False,
        )
    )
    batch_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "import_batch.id",
                ondelete="CASCADE",
                name="fk_oa_leave_batch_id_import_batch",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_oa_leave_employee_id_employee",
            ),
            nullable=False,
        )
    )
    source_row_number: int
    approval_no: str | None = Field(default=None, max_length=100)
    employee_name_raw: str = Field(max_length=100)
    department_raw: str = Field(max_length=100)
    leave_type_raw: str = Field(max_length=100)
    leave_kind: LeaveKind = Field(
        sa_column=_enum_column(LeaveKind, "ck_oa_leave_leave_kind", nullable=False)
    )
    days: Decimal = Field(max_digits=5, decimal_places=2)
    rest_start_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    rest_end_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    rest_start_date: date
    rest_end_date: date
    work_start_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    work_end_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    work_start_date: date | None = Field(default=None)
    work_end_date: date | None = Field(default=None)
    balance_days_declared: Decimal | None = Field(
        default=None, max_digits=6, decimal_places=2
    )
    reason: str | None = Field(default=None, max_length=500)
    approval_result_raw: str = Field(max_length=50)
    approval_status_raw: str = Field(max_length=50)
    raw_row: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class AttendanceDayResult(SQLModel, table=True):
    __tablename__ = "attendance_day_result"
    __table_args__ = (
        UniqueConstraint(
            "attendance_month_id",
            "employee_id",
            "work_date",
            name="uq_attendance_day_result_month_employee_date",
        ),
        Index("ix_attendance_day_result_company_date", "company_id", "work_date"),
        Index(
            "ix_attendance_day_result_employee_date",
            "employee_id",
            "work_date",
        ),
        Index("ix_attendance_day_result_calc_run", "calc_run_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_attendance_day_result_company_id_company",
            ),
            nullable=False,
        )
    )
    attendance_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "attendance_month.id",
                ondelete="CASCADE",
                name=("fk_attendance_day_result_attendance_month_id_attendance_month"),
            ),
            nullable=False,
        )
    )
    calc_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_run.id",
                ondelete="RESTRICT",
                name="fk_attendance_day_result_calc_run_id_calc_run",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_attendance_day_result_employee_id_employee",
            ),
            nullable=False,
        )
    )
    work_date: date
    day_type: DayType = Field(
        sa_column=_enum_column(
            DayType, "ck_attendance_day_result_day_type", nullable=False
        )
    )
    roster_state: ResultRosterState = Field(
        sa_column=_enum_column(
            ResultRosterState,
            "ck_attendance_day_result_roster_state",
            nullable=False,
        )
    )
    day_status: DayStatus = Field(
        sa_column=_enum_column(
            DayStatus, "ck_attendance_day_result_day_status", nullable=False
        )
    )
    day_flags: list[str] = Field(sa_column=_jsonb_column(nullable=False, default=list))
    attendance_fraction: Decimal = Field(
        default=Decimal("0"), max_digits=3, decimal_places=1
    )
    scheduled_minutes: int = Field(default=0)
    worked_minutes: int = Field(default=0)
    late_minutes: int = Field(default=0)
    early_minutes: int = Field(default=0)
    late_count: int = Field(default=0)
    early_count: int = Field(default=0)
    missing_punch_count: int = Field(default=0)
    leave_kind: LeaveKind | None = Field(
        default=None,
        sa_column=_enum_column(
            LeaveKind, "ck_attendance_day_result_leave_kind", nullable=True
        ),
    )
    leave_days: Decimal = Field(default=Decimal("0"), max_digits=3, decimal_places=1)
    paid_leave_days: Decimal = Field(
        default=Decimal("0"), max_digits=3, decimal_places=1
    )
    unpaid_leave_days: Decimal = Field(
        default=Decimal("0"), max_digits=3, decimal_places=1
    )
    comp_leave_days: Decimal = Field(
        default=Decimal("0"), max_digits=3, decimal_places=1
    )
    trip_kind: TripKind | None = Field(
        default=None,
        sa_column=_enum_column(
            TripKind, "ck_attendance_day_result_trip_kind", nullable=True
        ),
    )
    trip_fraction: Decimal = Field(default=Decimal("0"), max_digits=3, decimal_places=1)
    ot_weekday_minutes: int = Field(default=0)
    ot_weekend_minutes: int = Field(default=0)
    ot_holiday_minutes: int = Field(default=0)
    comp_offset_minutes: int = Field(default=0)
    comp_offset_unused_minutes: int = Field(default=0)
    absent_deduct_amount: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    late_deduct_amount: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    early_deduct_amount: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    missing_punch_deduct_amount: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    deduction_total: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    is_adjusted: bool = Field(default=False)
    adjustment_id: uuid.UUID | None = Field(default=None, sa_type=sa.UUID(as_uuid=True))
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class AttendanceDayShiftResult(SQLModel, table=True):
    __tablename__ = "attendance_day_shift_result"
    __table_args__ = (
        UniqueConstraint(
            "day_result_id", "seq", name="uq_attendance_day_shift_result_day_seq"
        ),
        Index("ix_attendance_day_shift_result_calc_run", "calc_run_id"),
        Index(
            "ix_attendance_day_shift_result_employee_date",
            "employee_id",
            "work_date",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_attendance_day_shift_result_company_id_company",
            ),
            nullable=False,
        )
    )
    day_result_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "attendance_day_result.id",
                ondelete="CASCADE",
                name="fk_attendance_day_shift_result_day_id_attendance_day_result",
            ),
            nullable=False,
        )
    )
    calc_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_run.id",
                ondelete="RESTRICT",
                name=("fk_attendance_day_shift_result_calc_run_id_calc_run"),
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_attendance_day_shift_result_employee_id_employee",
            ),
            nullable=False,
        )
    )
    work_date: date
    seq: int
    shift_id: uuid.UUID = Field(sa_type=sa.UUID(as_uuid=True))
    shift_code: str = Field(max_length=32)
    shift_name: str = Field(max_length=100)
    start_time: time
    end_time: time
    cross_day: bool
    break_start: time | None = Field(default=None)
    break_end: time | None = Field(default=None)
    rest_minutes: int
    shift_status: DayStatus = Field(
        sa_column=_enum_column(
            DayStatus,
            "ck_attendance_day_shift_result_shift_status",
            nullable=False,
        )
    )
    shift_flags: list[str] = Field(
        sa_column=_jsonb_column(nullable=False, default=list)
    )
    punch_in_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    punch_out_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    break_out_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    break_in_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    scheduled_minutes: int = Field(default=0)
    worked_minutes: int = Field(default=0)
    late_minutes: int = Field(default=0)
    early_minutes: int = Field(default=0)
    missing_punch_count: int = Field(default=0)
    ot_minutes: int = Field(default=0)
    comp_offset_minutes: int = Field(default=0)
    leave_days: Decimal = Field(default=Decimal("0"), max_digits=3, decimal_places=1)
    note: str | None = Field(default=None, max_length=500)


class AttendanceMonthSummary(SQLModel, table=True):
    __tablename__ = "attendance_month_summary"
    __table_args__ = (
        UniqueConstraint(
            "attendance_month_id",
            "employee_id",
            name="uq_attendance_month_summary_month_employee",
        ),
        Index("ix_attendance_month_summary_calc_run", "calc_run_id"),
        Index(
            "ix_attendance_month_summary_company_employee",
            "company_id",
            "employee_id",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_attendance_month_summary_company_id_company",
            ),
            nullable=False,
        )
    )
    attendance_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "attendance_month.id",
                ondelete="CASCADE",
                name="fk_attendance_month_summary_month_id_attendance_month",
            ),
            nullable=False,
        )
    )
    calc_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_run.id",
                ondelete="RESTRICT",
                name="fk_attendance_month_summary_calc_run_id_calc_run",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_attendance_month_summary_employee_id_employee",
            ),
            nullable=False,
        )
    )
    weekday_full: Decimal = Field(default=Decimal("0"), max_digits=5, decimal_places=1)
    weekend_full: Decimal = Field(default=Decimal("0"), max_digits=5, decimal_places=1)
    weekday_attended: Decimal = Field(
        default=Decimal("0"), max_digits=5, decimal_places=1
    )
    weekend_attended: Decimal = Field(
        default=Decimal("0"), max_digits=5, decimal_places=1
    )
    paid_leave_days: Decimal = Field(
        default=Decimal("0"), max_digits=5, decimal_places=1
    )
    unpaid_leave_days: Decimal = Field(
        default=Decimal("0"), max_digits=5, decimal_places=1
    )
    comp_leave_days: Decimal = Field(
        default=Decimal("0"), max_digits=5, decimal_places=1
    )
    trip_days: Decimal = Field(default=Decimal("0"), max_digits=5, decimal_places=1)
    ot_weekday_minutes: int = Field(default=0)
    ot_weekend_minutes: int = Field(default=0)
    ot_holiday_minutes: int = Field(default=0)
    ot_weekday_hours: Decimal = Field(
        default=Decimal("0"), max_digits=7, decimal_places=2
    )
    ot_weekend_hours: Decimal = Field(
        default=Decimal("0"), max_digits=7, decimal_places=2
    )
    ot_holiday_hours: Decimal = Field(
        default=Decimal("0"), max_digits=7, decimal_places=2
    )
    comp_leave_used_hours: Decimal = Field(
        default=Decimal("0"), max_digits=7, decimal_places=2
    )
    comp_offset_unused_minutes: int = Field(default=0)
    late_count: int = Field(default=0)
    late_minutes: int = Field(default=0)
    early_count: int = Field(default=0)
    early_minutes: int = Field(default=0)
    missing_punch_count: int = Field(default=0)
    absent_days: int = Field(default=0)
    worked_minutes: int = Field(default=0)
    attendance_deduct: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    is_adjusted: bool = Field(default=False)
    calc_version: str = Field(max_length=32)
    rules_version: str = Field(max_length=64)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class AttendanceResultAdjustment(SQLModel, table=True):
    __tablename__ = "attendance_result_adjustment"
    __table_args__ = (
        Index(
            "uq_attendance_result_adjustment_month_employee_date_active",
            "attendance_month_id",
            "employee_id",
            "work_date",
            unique=True,
            postgresql_where=sa.text("status = 'active'"),
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_attendance_result_adjustment_company_id_company",
            ),
            nullable=False,
        )
    )
    attendance_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "attendance_month.id",
                ondelete="CASCADE",
                name="fk_attendance_result_adjustment_month_id_attendance_month",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_attendance_result_adjustment_employee_id_employee",
            ),
            nullable=False,
        )
    )
    work_date: date
    version: int
    status: AdjustmentStatus = Field(
        sa_column=_enum_column(
            AdjustmentStatus,
            "ck_attendance_result_adjustment_status",
            nullable=False,
        )
    )
    original_values: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    adjusted_values: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    reason: str = Field(max_length=500)
    adjusted_by: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_attendance_result_adjustment_adjusted_by_user",
            ),
            nullable=False,
        )
    )
    adjusted_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    calc_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_run.id",
                ondelete="RESTRICT",
                name=("fk_attendance_result_adjustment_calc_run_id_calc_run"),
            ),
            nullable=False,
        )
    )


# Payroll models. These are table-only: every reference is an explicit
# foreign-key column and the service layer composes queries. Primary keys are
# UUID v7 generated in Python, enum columns are VARCHAR + CHECK via non-native
# ``SAEnum``, and timestamps are TIMESTAMPTZ generated in Python. Migrations
# are the contract; see docs/specs/payroll-management.md sections 4 and 16.

_COMPOSITION_AMOUNT_FIELDS: tuple[str, ...] = (
    "base_salary",
    "hightemp_subsidy",
    "performance_salary",
    "overtime_pay",
    "confidentiality_allowance",
    "social_subsidy",
    "noncompete_subsidy",
)
_COMPOSITION_TOTAL_EXPRESSION = "total_package = " + " + ".join(
    _COMPOSITION_AMOUNT_FIELDS
)


class SalaryFieldDef(SQLModel, table=True):
    __tablename__ = "salary_field_def"
    __table_args__ = (
        UniqueConstraint("field_key", name="uq_salary_field_def_field_key"),
        UniqueConstraint("label", name="uq_salary_field_def_label"),
        Index(
            "uq_salary_field_def_source_key",
            "source_key",
            unique=True,
            postgresql_where=sa.text("source_key IS NOT NULL"),
        ),
        Index(
            "ix_salary_field_def_category_display_order",
            "category",
            "display_order",
        ),
        sa.CheckConstraint(
            "field_key ~ '^[a-z][a-z0-9_]{0,63}$'",
            name="ck_salary_field_def_field_key_pattern",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    field_key: str = Field(max_length=64)
    label: str = Field(max_length=100)
    category: SalaryFieldCategory = Field(
        sa_column=_enum_column(
            SalaryFieldCategory,
            "ck_salary_field_def_category",
            nullable=False,
            length=16,
        )
    )
    calc_mode: SalaryFieldCalcMode = Field(
        sa_column=_enum_column(
            SalaryFieldCalcMode,
            "ck_salary_field_def_calc_mode",
            nullable=False,
            length=16,
        )
    )
    source_key: str | None = Field(default=None, max_length=64)
    fixed_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    default_formula: str | None = Field(default=None, sa_type=sa.Text())
    display_order: int = Field(default=0)
    visible: bool = Field(default=True)
    is_system: bool = Field(default=False)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class CompensationComposition(SQLModel, table=True):
    __tablename__ = "compensation_composition"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "comp_code",
            name="uq_compensation_composition_company_comp_code",
        ),
        Index(
            "ix_compensation_composition_company_active",
            "company_id",
            "is_active",
        ),
        sa.CheckConstraint(
            "comp_code ~ '^[A-Z0-9_-]{1,32}$'",
            name="ck_compensation_composition_comp_code_pattern",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_compensation_composition_company_id_company",
            ),
            nullable=False,
        )
    )
    comp_code: str = Field(max_length=32)
    comp_name: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class CompensationCompositionVersion(SQLModel, table=True):
    __tablename__ = "compensation_composition_version"
    __table_args__ = (
        UniqueConstraint(
            "comp_id",
            "version_no",
            name="uq_compensation_composition_version_comp_version",
        ),
        sa.CheckConstraint("version_no >= 1", name="ck_comp_ver_version_positive"),
        *(
            sa.CheckConstraint(
                f"{field} >= 0", name=f"ck_comp_ver_{field}_non_negative"
            )
            for field in _COMPOSITION_AMOUNT_FIELDS
        ),
        sa.CheckConstraint(
            _COMPOSITION_TOTAL_EXPRESSION, name="ck_comp_ver_total_package_sum"
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    comp_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "compensation_composition.id",
                ondelete="RESTRICT",
                name="fk_comp_version_comp_id_compensation_composition",
            ),
            nullable=False,
        )
    )
    version_no: int
    base_salary: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    hightemp_subsidy: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    performance_salary: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    overtime_pay: Decimal = Field(default=Decimal("0"), max_digits=14, decimal_places=2)
    confidentiality_allowance: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    social_subsidy: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    noncompete_subsidy: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )
    total_package: Decimal = Field(max_digits=14, decimal_places=2)
    change_note: str | None = Field(default=None, max_length=500)
    created_by: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_compensation_composition_version_created_by_user",
            ),
            nullable=True,
        ),
    )
    created_by_name: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class WorkdayParam(SQLModel, table=True):
    __tablename__ = "workday_param"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "workday_code",
            name="uq_workday_param_company_workday_code",
        ),
        sa.CheckConstraint(
            "workday_code ~ '^[A-Z0-9_-]{1,32}$'",
            name="ck_workday_param_workday_code_pattern",
        ),
        sa.CheckConstraint(
            "avg_pay_days > 0", name="ck_workday_param_avg_pay_days_positive"
        ),
        sa.CheckConstraint(
            "work_hours > 0", name="ck_workday_param_work_hours_positive"
        ),
        sa.CheckConstraint(
            "ot_mult_weekday >= 1", name="ck_workday_param_ot_mult_weekday_min"
        ),
        sa.CheckConstraint(
            "ot_mult_weekend >= 1", name="ck_workday_param_ot_mult_weekend_min"
        ),
        sa.CheckConstraint(
            "ot_mult_holiday >= 1", name="ck_workday_param_ot_mult_holiday_min"
        ),
        sa.CheckConstraint(
            "min_wage >= 0", name="ck_workday_param_min_wage_non_negative"
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_workday_param_company_id_company",
            ),
            nullable=False,
        )
    )
    workday_code: str = Field(max_length=32)
    workday_name: str = Field(max_length=100)
    avg_pay_days: Decimal = Field(
        default=Decimal("21.75"), max_digits=5, decimal_places=2
    )
    work_hours: Decimal = Field(max_digits=4, decimal_places=2)
    ot_mult_weekday: Decimal = Field(
        default=Decimal("1.5"), max_digits=4, decimal_places=2
    )
    ot_mult_weekend: Decimal = Field(
        default=Decimal("2.0"), max_digits=4, decimal_places=2
    )
    ot_mult_holiday: Decimal = Field(
        default=Decimal("3.0"), max_digits=4, decimal_places=2
    )
    min_wage: Decimal = Field(max_digits=14, decimal_places=2)
    min_wage_note: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class CalcScheme(SQLModel, table=True):
    __tablename__ = "calc_scheme"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "calc_code", name="uq_calc_scheme_company_calc_code"
        ),
        sa.CheckConstraint(
            "calc_code ~ '^[A-Z0-9_-]{1,32}$'",
            name="ck_calc_scheme_calc_code_pattern",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_calc_scheme_company_id_company",
            ),
            nullable=False,
        )
    )
    calc_code: str = Field(max_length=32)
    calc_name: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class CalcSchemeFormula(SQLModel, table=True):
    __tablename__ = "calc_scheme_formula"
    __table_args__ = (
        UniqueConstraint(
            "calc_scheme_id",
            "field_def_id",
            name="uq_calc_scheme_formula_scheme_field",
        ),
        Index("ix_calc_scheme_formula_field_def_id", "field_def_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    calc_scheme_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_scheme.id",
                ondelete="CASCADE",
                name="fk_calc_scheme_formula_calc_scheme_id_calc_scheme",
            ),
            nullable=False,
        )
    )
    field_def_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "salary_field_def.id",
                ondelete="RESTRICT",
                name="fk_calc_scheme_formula_field_def_id_salary_field_def",
            ),
            nullable=False,
        )
    )
    formula_expr: str = Field(sa_type=sa.Text())
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PositionPayrollConfig(SQLModel, table=True):
    __tablename__ = "position_payroll_config"
    __table_args__ = (
        UniqueConstraint("position_id", name="uq_position_payroll_config_position_id"),
        Index("ix_position_payroll_config_comp_id", "comp_id"),
        Index("ix_position_payroll_config_calc_scheme_id", "calc_scheme_id"),
        Index("ix_position_payroll_config_workday_param_id", "workday_param_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    position_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "position.id",
                ondelete="CASCADE",
                name="fk_position_payroll_config_position_id_position",
            ),
            nullable=False,
        )
    )
    comp_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "compensation_composition.id",
                ondelete="RESTRICT",
                name="fk_position_payroll_config_comp_id_compensation_composition",
            ),
            nullable=False,
        )
    )
    calc_scheme_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_scheme.id",
                ondelete="RESTRICT",
                name="fk_position_payroll_config_calc_scheme_id_calc_scheme",
            ),
            nullable=False,
        )
    )
    workday_param_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "workday_param.id",
                ondelete="RESTRICT",
                name="fk_position_payroll_config_workday_param_id_workday_param",
            ),
            nullable=False,
        )
    )
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PayrollGlobalParam(SQLModel, table=True):
    __tablename__ = "payroll_global_param"
    __table_args__ = (
        UniqueConstraint("key", name="uq_payroll_global_param_key"),
        sa.CheckConstraint(
            "(value_type = 'number' AND numeric_value IS NOT NULL "
            "AND json_value IS NULL) "
            "OR (value_type = 'json' AND numeric_value IS NULL "
            "AND json_value IS NOT NULL)",
            name="ck_payroll_global_param_value_exclusive",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    key: str = Field(max_length=64)
    label: str = Field(max_length=100)
    category: str = Field(max_length=32)
    value_type: PayrollGlobalParamType = Field(
        sa_column=_enum_column(
            PayrollGlobalParamType,
            "ck_payroll_global_param_value_type",
            nullable=False,
            length=16,
        )
    )
    numeric_value: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    json_value: Any = Field(default=None, sa_column=_jsonb_column(nullable=True))
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PayrollConfigRevision(SQLModel, table=True):
    __tablename__ = "payroll_config_revision"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "version_no",
            name="uq_payroll_config_revision_entity_version",
        ),
        Index(
            "ix_payroll_config_revision_entity",
            "entity_type",
            "entity_id",
            sa.desc("changed_at"),
        ),
        sa.CheckConstraint(
            "version_no >= 1", name="ck_payroll_config_revision_version_positive"
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    entity_type: PayrollConfigEntityType = Field(
        sa_column=_enum_column(
            PayrollConfigEntityType,
            "ck_payroll_config_revision_entity_type",
            nullable=False,
            length=32,
        )
    )
    entity_id: uuid.UUID = Field(sa_type=sa.UUID(as_uuid=True))
    version_no: int
    snapshot: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    change_note: str | None = Field(default=None, max_length=500)
    changed_by: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_config_revision_changed_by_user",
            ),
            nullable=True,
        ),
    )
    changed_by_name: str | None = Field(default=None, max_length=100)
    changed_at: datetime = Field(sa_type=sa.DateTime(timezone=True))


class PayrollMonth(SQLModel, table=True):
    __tablename__ = "payroll_month"
    __table_args__ = (
        UniqueConstraint("company_id", "month", name="uq_payroll_month_company_month"),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1", name="ck_payroll_month_first_day"
        ),
        sa.CheckConstraint(
            "input_version >= 0", name="ck_payroll_month_input_version_non_negative"
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_payroll_month_company_id_company",
            ),
            nullable=False,
        )
    )
    month: date
    status: PayrollMonthStatus = Field(
        default=PayrollMonthStatus.DRAFT,
        sa_column=_enum_column(
            PayrollMonthStatus,
            "ck_payroll_month_status",
            nullable=False,
            length=16,
        ),
    )
    input_version: int = Field(default=0)
    config_stale: bool = Field(default=False)
    config_stale_detail: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    calculated_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    confirmed_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    paid_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    unlock_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PayrollCalcRun(SQLModel, table=True):
    __tablename__ = "payroll_calc_run"
    __table_args__ = (
        Index(
            "ix_payroll_calc_run_month_started_at",
            "payroll_month_id",
            sa.desc("started_at"),
        ),
        Index("ix_payroll_calc_run_status", "status"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    payroll_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month.id",
                ondelete="CASCADE",
                name="fk_payroll_calc_run_payroll_month_id_payroll_month",
            ),
            nullable=False,
        )
    )
    trigger: PayrollCalcRunTrigger = Field(
        sa_column=_enum_column(
            PayrollCalcRunTrigger,
            "ck_payroll_calc_run_trigger",
            nullable=False,
            length=24,
        )
    )
    status: PayrollCalcRunStatus = Field(
        sa_column=_enum_column(
            PayrollCalcRunStatus,
            "ck_payroll_calc_run_status",
            nullable=False,
            length=16,
        )
    )
    config_snapshot_version: int
    config_snapshot: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    input_version: int
    input_snapshot: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    attendance_month_id: uuid.UUID | None = Field(
        default=None, sa_type=sa.UUID(as_uuid=True)
    )
    attendance_snapshot_id: uuid.UUID | None = Field(
        default=None, sa_type=sa.UUID(as_uuid=True)
    )
    attendance_snapshot_version: int | None = Field(default=None)
    attendance_calc_run_id: uuid.UUID | None = Field(
        default=None, sa_type=sa.UUID(as_uuid=True)
    )
    calc_version: str | None = Field(default=None, max_length=32)
    rules_version: str | None = Field(default=None, max_length=64)
    attendance_locked_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    summary: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    error_code: str | None = Field(default=None, max_length=50)
    error_message: str | None = Field(default=None, max_length=500)
    triggered_by: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_calc_run_triggered_by_user",
            ),
            nullable=True,
        ),
    )
    triggered_by_name: str | None = Field(default=None, max_length=100)
    started_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    finished_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )


class PayrollResult(SQLModel, table=True):
    __tablename__ = "payroll_result"
    __table_args__ = (
        UniqueConstraint(
            "payroll_month_id",
            "employee_id",
            name="uq_payroll_result_month_employee",
        ),
        Index("ix_payroll_result_month_dept_id", "payroll_month_id", "dept_id"),
        Index(
            "ix_payroll_result_month_position_id",
            "payroll_month_id",
            "position_id",
        ),
        Index(
            "ix_payroll_result_month_cost_org_id",
            "payroll_month_id",
            "cost_org_id",
        ),
        Index(
            "ix_payroll_result_month_cost_org_code",
            "payroll_month_id",
            "cost_org_code",
        ),
        Index("ix_payroll_result_company_dept_code", "company_id", "dept_code"),
        Index(
            "ix_payroll_result_company_cost_org_code",
            "company_id",
            "cost_org_code",
        ),
        Index("ix_payroll_result_dept_path_gin", "dept_path", postgresql_using="gin"),
        Index(
            "ix_payroll_result_cost_org_path_gin",
            "cost_org_path",
            postgresql_using="gin",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    payroll_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month.id",
                ondelete="CASCADE",
                name="fk_payroll_result_payroll_month_id_payroll_month",
            ),
            nullable=False,
        )
    )
    calc_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_calc_run.id",
                ondelete="CASCADE",
                name="fk_payroll_result_calc_run_id_payroll_calc_run",
            ),
            nullable=False,
        )
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_payroll_result_company_id_company",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_payroll_result_employee_id_employee",
            ),
            nullable=False,
        )
    )
    position_id: uuid.UUID = Field(sa_type=sa.UUID(as_uuid=True))
    dept_id: uuid.UUID = Field(sa_type=sa.UUID(as_uuid=True))
    cost_org_id: uuid.UUID | None = Field(default=None, sa_type=sa.UUID(as_uuid=True))
    calc_scheme_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "calc_scheme.id",
                ondelete="RESTRICT",
                name="fk_payroll_result_calc_scheme_id_calc_scheme",
            ),
            nullable=False,
        )
    )
    position_code: str = Field(max_length=32)
    position_name: str = Field(max_length=100)
    dept_code: str = Field(max_length=32)
    dept_name: str = Field(max_length=100)
    cost_org_code: str | None = Field(default=None, max_length=32)
    cost_org_name: str | None = Field(default=None, max_length=100)
    dept_path: list[Any] = Field(sa_column=_jsonb_column(nullable=False))
    cost_org_path: list[Any] = Field(sa_column=_jsonb_column(nullable=False))
    attendance_source: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PayrollResultValue(SQLModel, table=True):
    __tablename__ = "payroll_result_value"
    __table_args__ = (
        UniqueConstraint(
            "result_id",
            "field_def_id",
            name="uq_payroll_result_value_result_field",
        ),
        Index("ix_payroll_result_value_field_def_id", "field_def_id"),
        Index("ix_payroll_result_value_produced_by_run_id", "produced_by_run_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    result_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_result.id",
                ondelete="CASCADE",
                name="fk_payroll_result_value_result_id_payroll_result",
            ),
            nullable=False,
        )
    )
    field_def_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "salary_field_def.id",
                ondelete="RESTRICT",
                name="fk_payroll_result_value_field_def_id_salary_field_def",
            ),
            nullable=False,
        )
    )
    value: Decimal = Field(max_digits=18, decimal_places=4)
    source: PayrollResultSource = Field(
        sa_column=_enum_column(
            PayrollResultSource,
            "ck_payroll_result_value_source",
            nullable=False,
            length=16,
        )
    )
    produced_by_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_calc_run.id",
                ondelete="RESTRICT",
                name="fk_payroll_result_value_produced_by_run_id_payroll_calc_run",
            ),
            nullable=False,
        )
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PayrollMonthSnapshot(SQLModel, table=True):
    __tablename__ = "payroll_month_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "payroll_month_id",
            "version",
            name="uq_payroll_month_snapshot_month_version",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_payroll_month_snapshot_version_positive",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    payroll_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month.id",
                ondelete="CASCADE",
                name="fk_payroll_month_snapshot_payroll_month_id_payroll_month",
            ),
            nullable=False,
        )
    )
    calc_run_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_calc_run.id",
                ondelete="RESTRICT",
                name="fk_payroll_month_snapshot_calc_run_id_payroll_calc_run",
            ),
            nullable=False,
        )
    )
    version: int
    paid_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    paid_by: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_month_snapshot_paid_by_user",
            ),
            nullable=False,
        )
    )
    paid_by_name: str = Field(max_length=100)
    payload: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))


class PayrollMonthEvent(SQLModel, table=True):
    __tablename__ = "payroll_month_event"
    __table_args__ = (
        Index(
            "ix_payroll_month_event_month_created_at",
            "payroll_month_id",
            sa.desc("created_at"),
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    payroll_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month.id",
                ondelete="CASCADE",
                name="fk_payroll_month_event_payroll_month_id_payroll_month",
            ),
            nullable=False,
        )
    )
    event: PayrollMonthEventType = Field(
        sa_column=_enum_column(
            PayrollMonthEventType,
            "ck_payroll_month_event_event",
            nullable=False,
            length=16,
        )
    )
    from_status: str = Field(max_length=16)
    to_status: str = Field(max_length=16)
    calc_run_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_calc_run.id",
                ondelete="SET NULL",
                name="fk_payroll_month_event_calc_run_id_payroll_calc_run",
            ),
            nullable=True,
        ),
    )
    snapshot_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month_snapshot.id",
                ondelete="SET NULL",
                name="fk_payroll_month_event_snapshot_id_payroll_month_snapshot",
            ),
            nullable=True,
        ),
    )
    reason: str | None = Field(default=None, max_length=500)
    operator_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_month_event_operator_id_user",
            ),
            nullable=True,
        ),
    )
    operator_name: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(sa_type=sa.DateTime(timezone=True))


class PayrollMonthInput(SQLModel, table=True):
    __tablename__ = "payroll_month_input"
    __table_args__ = (
        UniqueConstraint(
            "payroll_month_id",
            "employee_id",
            name="uq_payroll_month_input_month_employee",
        ),
        Index("ix_payroll_month_input_employee_id", "employee_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    payroll_month_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month.id",
                ondelete="CASCADE",
                name="fk_payroll_month_input_payroll_month_id_payroll_month",
            ),
            nullable=False,
        )
    )
    employee_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="RESTRICT",
                name="fk_payroll_month_input_employee_id_employee",
            ),
            nullable=False,
        )
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PayrollInputValue(SQLModel, table=True):
    __tablename__ = "payroll_input_value"
    __table_args__ = (
        UniqueConstraint(
            "input_id",
            "field_def_id",
            name="uq_payroll_input_value_input_field",
        ),
        Index("ix_payroll_input_value_field_def_id", "field_def_id"),
        Index("ix_payroll_input_value_source_batch_id", "source_batch_id"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    input_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month_input.id",
                ondelete="CASCADE",
                name="fk_payroll_input_value_input_id_payroll_month_input",
            ),
            nullable=False,
        )
    )
    field_def_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "salary_field_def.id",
                ondelete="RESTRICT",
                name="fk_payroll_input_value_field_def_id_salary_field_def",
            ),
            nullable=False,
        )
    )
    value: Decimal = Field(default=Decimal("0"), max_digits=18, decimal_places=4)
    source: PayrollInputSource = Field(
        sa_column=_enum_column(
            PayrollInputSource,
            "ck_payroll_input_value_source",
            nullable=False,
            length=16,
        )
    )
    source_batch_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_import_batch.id",
                ondelete="SET NULL",
                name="fk_payroll_input_value_source_batch_id_payroll_import_batch",
            ),
            nullable=True,
        ),
    )
    updated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_input_value_updated_by_user",
            ),
            nullable=True,
        ),
    )
    updated_by_name: str | None = Field(default=None, max_length=100)
    updated_at: datetime = Field(sa_type=sa.DateTime(timezone=True))


class PayrollImportBatch(SQLModel, table=True):
    __tablename__ = "payroll_import_batch"
    __table_args__ = (
        Index(
            "ix_payroll_import_batch_company_month_status_created_at",
            "company_id",
            "month",
            "status",
            sa.desc("created_at"),
        ),
        Index(
            "uq_payroll_import_batch_company_month_committed",
            "company_id",
            "month",
            unique=True,
            postgresql_where=sa.text("status = 'committed'"),
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1",
            name="ck_payroll_import_batch_month_first_day",
        ),
        sa.CheckConstraint(
            "source_rows >= 0",
            name="ck_payroll_import_batch_source_rows_non_negative",
        ),
        sa.CheckConstraint(
            "valid_records >= 0",
            name="ck_payroll_import_batch_valid_records_non_negative",
        ),
        sa.CheckConstraint(
            "error_records >= 0",
            name="ck_payroll_import_batch_error_records_non_negative",
        ),
        sa.CheckConstraint(
            "warning_records >= 0",
            name="ck_payroll_import_batch_warning_records_non_negative",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_payroll_import_batch_company_id_company",
            ),
            nullable=False,
        )
    )
    month: date
    status: PayrollImportBatchStatus = Field(
        sa_column=_enum_column(
            PayrollImportBatchStatus,
            "ck_payroll_import_batch_status",
            nullable=False,
            length=16,
        )
    )
    source: PayrollImportBatchSource = Field(
        sa_column=_enum_column(
            PayrollImportBatchSource,
            "ck_payroll_import_batch_source",
            nullable=False,
            length=16,
        )
    )
    file_name: str | None = Field(default=None, max_length=255)
    file_size: int | None = Field(default=None)
    file_sha256: str | None = Field(default=None, max_length=64)
    sheet_name: str | None = Field(default=None, max_length=100)
    header_row_number: int | None = Field(default=None)
    header_columns: list[Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    column_mapping: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    parser_version: str = Field(max_length=32)
    source_rows: int = Field(default=0)
    valid_records: int = Field(default=0)
    error_records: int = Field(default=0)
    warning_records: int = Field(default=0)
    warning_counts: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    operator_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_import_batch_operator_id_user",
            ),
            nullable=True,
        ),
    )
    operator_name: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    committed_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    superseded_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    discarded_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    expires_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    superseded_by_batch_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_import_batch.id",
                ondelete="SET NULL",
                name="fk_payroll_import_batch_superseded_by_batch_id",
            ),
            nullable=True,
        ),
    )
    discard_reason: str | None = Field(default=None, max_length=500)
    payroll_month_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month.id",
                ondelete="SET NULL",
                name="fk_payroll_import_batch_payroll_month_id_payroll_month",
            ),
            nullable=True,
        ),
    )


class PayrollImportBatchRow(SQLModel, table=True):
    __tablename__ = "payroll_import_batch_row"
    __table_args__ = (
        Index("ix_payroll_import_batch_row_batch_status", "batch_id", "status"),
        Index(
            "ix_payroll_import_batch_row_batch_row",
            "batch_id",
            "source_row_number",
        ),
        sa.CheckConstraint(
            "source_row_number >= 1",
            name="ck_payroll_import_batch_row_source_row_number_positive",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    batch_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_import_batch.id",
                ondelete="CASCADE",
                name="fk_payroll_import_batch_row_batch_id_payroll_import_batch",
            ),
            nullable=False,
        )
    )
    source_row_number: int
    employee_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "employee.id",
                ondelete="SET NULL",
                name="fk_payroll_import_batch_row_employee_id_employee",
            ),
            nullable=True,
        ),
    )
    employee_no_raw: str | None = Field(default=None, max_length=64)
    values: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    status: PayrollImportRowStatus = Field(
        sa_column=_enum_column(
            PayrollImportRowStatus,
            "ck_payroll_import_batch_row_status",
            nullable=False,
            length=16,
        )
    )
    error_code: str | None = Field(default=None, max_length=50)
    error_message: str | None = Field(default=None, max_length=500)
    warnings: list[Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    raw_row: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )


class PayrollImportMappingTemplate(SQLModel, table=True):
    __tablename__ = "payroll_import_mapping_template"
    __table_args__ = (
        UniqueConstraint(
            "company_id", name="uq_payroll_import_mapping_template_company"
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="CASCADE",
                name="fk_payroll_import_mapping_template_company_id_company",
            ),
            nullable=False,
        )
    )
    column_mapping: dict[str, Any] = Field(sa_column=_jsonb_column(nullable=False))
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )


class PayrollExport(SQLModel, table=True):
    __tablename__ = "payroll_export"
    __table_args__ = (
        Index(
            "ix_payroll_export_company_month_created_at",
            "company_id",
            "month",
            sa.desc("created_at"),
        ),
        Index("ix_payroll_export_status_created_at", "status", "created_at"),
        Index("ix_payroll_export_expires_at", "expires_at"),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month) = 1",
            name="ck_payroll_export_month_first_day",
        ),
        sa.CheckConstraint(
            "employee_count >= 0",
            name="ck_payroll_export_employee_count_non_negative",
        ),
        sa.CheckConstraint(
            "progress_done >= 0",
            name="ck_payroll_export_progress_done_non_negative",
        ),
        sa.CheckConstraint(
            "progress_total >= 0",
            name="ck_payroll_export_progress_total_non_negative",
        ),
        sa.CheckConstraint(
            "download_count >= 0",
            name="ck_payroll_export_download_count_non_negative",
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid7,
        primary_key=True,
        sa_type=sa.UUID(as_uuid=True),
    )
    company_id: uuid.UUID = Field(
        sa_column=_uuid_column(
            ForeignKey(
                "company.id",
                ondelete="RESTRICT",
                name="fk_payroll_export_company_id_company",
            ),
            nullable=False,
        )
    )
    month: date
    export_type: PayrollExportType = Field(
        sa_column=_enum_column(
            PayrollExportType,
            "ck_payroll_export_export_type",
            nullable=False,
            length=32,
        )
    )
    format: str = Field(max_length=8)
    mode: str | None = Field(default=None, max_length=16)
    snapshot_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_month_snapshot.id",
                ondelete="SET NULL",
                name="fk_payroll_export_snapshot_id_payroll_month_snapshot",
            ),
            nullable=True,
        ),
    )
    snapshot_version: int | None = Field(default=None)
    calc_run_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "payroll_calc_run.id",
                ondelete="SET NULL",
                name="fk_payroll_export_calc_run_id_payroll_calc_run",
            ),
            nullable=True,
        ),
    )
    month_status_at_creation: str | None = Field(default=None, max_length=16)
    filter: dict[str, Any] | None = Field(
        default=None, sa_column=_jsonb_column(nullable=True)
    )
    filter_hash: str | None = Field(default=None, max_length=64)
    employee_count: int = Field(default=0)
    status: PayrollExportStatus = Field(
        sa_column=_enum_column(
            PayrollExportStatus,
            "ck_payroll_export_status",
            nullable=False,
            length=16,
        )
    )
    progress_done: int = Field(default=0)
    progress_total: int = Field(default=0)
    error_code: str | None = Field(default=None, max_length=50)
    error_message: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=get_datetime_utc, sa_type=sa.DateTime(timezone=True)
    )
    started_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    finished_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    artifact_path: str | None = Field(default=None, max_length=500)
    artifact_size: int | None = Field(default=None, sa_type=sa.BigInteger())
    expires_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    artifact_deleted_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
    operator_id: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_export_operator_id_user",
            ),
            nullable=True,
        ),
    )
    operator_name: str | None = Field(default=None, max_length=100)
    template_version: str | None = Field(default=None, max_length=32)
    download_count: int = Field(default=0)
    last_downloaded_by: uuid.UUID | None = Field(
        default=None,
        sa_column=_uuid_column(
            ForeignKey(
                "user.id",
                ondelete="RESTRICT",
                name="fk_payroll_export_last_downloaded_by_user",
            ),
            nullable=True,
        ),
    )
    last_downloaded_by_name: str | None = Field(default=None, max_length=100)
    last_downloaded_at: datetime | None = Field(
        default=None, sa_type=sa.DateTime(timezone=True)
    )
