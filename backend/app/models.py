import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from pydantic import EmailStr
from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.enums import ContractType, EmployeeStatus, Gender


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_column(*constraints: Any, nullable: bool) -> Column[Any]:
    return Column(sa.UUID(as_uuid=True), *constraints, nullable=nullable)


def _enum_column(
    enum_type: type[StrEnum], constraint_name: str, *, nullable: bool
) -> Column[Any]:
    return Column(
        SAEnum(
            enum_type,
            native_enum=False,
            create_constraint=True,
            name=constraint_name,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=nullable,
    )


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
