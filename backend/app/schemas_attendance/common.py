"""Shared request/response conventions for attendance schemas.

Write models reject unknown fields so immutable identifiers cannot be changed
through an update payload. Decimal public fields always serialize as strings,
matching the Basic Management API contract.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AfterValidator, BeforeValidator, Field, PlainSerializer
from sqlmodel import SQLModel
from sqlmodel._compat import SQLModelConfig

MONTH_PATTERN = r"^[0-9]{4}-(0[1-9]|1[0-2])$"


def _month_from_value(value: Any) -> Any:
    """Accept a stored first-of-month date and expose it as ``YYYY-MM``."""
    if isinstance(value, datetime):
        return value.date().strftime("%Y-%m")
    if isinstance(value, date):
        return value.strftime("%Y-%m")
    return value


def _check_month_year(value: str) -> str:
    if value[:4] == "0000":
        raise ValueError("月份格式不正确")
    return value


MonthString = Annotated[
    str,
    BeforeValidator(_month_from_value),
    Field(pattern=MONTH_PATTERN, examples=["2026-09"]),
    AfterValidator(_check_month_year),
]
DecimalString = Annotated[Decimal, PlainSerializer(str, return_type=str)]


class WriteModel(SQLModel):
    model_config = SQLModelConfig(extra="forbid")


class ReadModel(SQLModel):
    model_config = SQLModelConfig(from_attributes=True)


class Message(SQLModel):
    message: str


class EmployeeDisplay(SQLModel):
    employee_id: uuid.UUID
    employee_no: str
    employee_name: str
    department_id: uuid.UUID | None = None
    department_name: str | None = None


class DepartmentDisplay(SQLModel):
    department_id: uuid.UUID
    department_name: str
