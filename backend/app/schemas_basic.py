"""Basic Management request and response schemas.

Write schemas reject unknown fields so immutable identifiers (business codes and
``company_id``) cannot be changed through a PATCH. Services own display
enrichment, filtering, and business rules.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator
from sqlmodel import SQLModel
from sqlmodel._compat import SQLModelConfig

from app.enums import EmployeeStatus
from app.services.common import normalize_code

CODE_PATTERN = r"^[A-Z0-9_-]{1,32}$"


def normalize_note(value: object) -> object:
    """Treat an empty note as an omitted note."""
    return None if value == "" else value


class CompanyCreate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    company_code: str = Field(min_length=1, max_length=32, pattern=CODE_PATTERN)
    company_name: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    note: str | None = Field(default=None, max_length=500)

    @field_validator("company_code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> Any:
        return normalize_code(value) if isinstance(value, str) else value

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: Any) -> Any:
        return normalize_note(value)


class CompanyUpdate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    company_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: Any) -> Any:
        return normalize_note(value)

    @field_validator("company_name", "is_active")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        # Defaults are not validated, so this only fires for an explicit null.
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class CompanyPublic(SQLModel):
    model_config = SQLModelConfig(from_attributes=True)

    id: uuid.UUID
    company_code: str
    company_name: str
    is_active: bool
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class CompaniesPublic(SQLModel):
    data: list[CompanyPublic]
    count: int


class DepartmentCreate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    dept_code: str = Field(min_length=1, max_length=32, pattern=CODE_PATTERN)
    dept_name: str = Field(min_length=1, max_length=100)
    company_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    order_no: int = 0
    is_active: bool = True
    note: str | None = Field(default=None, max_length=500)

    @field_validator("dept_code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> Any:
        return normalize_code(value) if isinstance(value, str) else value

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: Any) -> Any:
        return normalize_note(value)


class DepartmentUpdate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    dept_name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    order_no: int | None = None
    is_active: bool | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: Any) -> Any:
        return normalize_note(value)

    @field_validator("dept_name", "order_no", "is_active")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        # Defaults are not validated, so this only fires for an explicit null.
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class DepartmentPublic(SQLModel):
    model_config = SQLModelConfig(from_attributes=True)

    id: uuid.UUID
    dept_code: str
    dept_name: str
    company_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    order_no: int
    is_active: bool
    note: str | None = None
    created_at: datetime
    updated_at: datetime
    company_name: str
    parent_name: str | None = None
    manager_name: str | None = None
    manager_status: EmployeeStatus | None = None


class DepartmentTreeNode(DepartmentPublic):
    children: list[DepartmentTreeNode] = Field(default_factory=list)


class DepartmentsPublic(SQLModel):
    data: list[DepartmentPublic]
    count: int


class DepartmentTreePublic(SQLModel):
    data: list[DepartmentTreeNode]


class PositionCreate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    position_code: str = Field(min_length=1, max_length=32, pattern=CODE_PATTERN)
    position_name: str = Field(min_length=1, max_length=100)
    company_id: uuid.UUID
    dept_id: uuid.UUID | None = None
    order_no: int = 0
    is_active: bool = True
    note: str | None = Field(default=None, max_length=500)

    @field_validator("position_code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> Any:
        return normalize_code(value) if isinstance(value, str) else value

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: Any) -> Any:
        return normalize_note(value)


class PositionUpdate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    position_name: str | None = Field(default=None, min_length=1, max_length=100)
    dept_id: uuid.UUID | None = None
    order_no: int | None = None
    is_active: bool | None = None
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def _normalize_note(cls, value: Any) -> Any:
        return normalize_note(value)

    @field_validator("position_name", "order_no", "is_active")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        # Defaults are not validated, so this only fires for an explicit null.
        if value is None:
            raise ValueError("该字段不能为空")
        return value


class PositionPublic(SQLModel):
    model_config = SQLModelConfig(from_attributes=True)

    id: uuid.UUID
    position_code: str
    position_name: str
    company_id: uuid.UUID
    dept_id: uuid.UUID | None = None
    order_no: int
    is_active: bool
    note: str | None = None
    created_at: datetime
    updated_at: datetime
    company_name: str
    dept_name: str | None = None


class PositionsPublic(SQLModel):
    data: list[PositionPublic]
    count: int
