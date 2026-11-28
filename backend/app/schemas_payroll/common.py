"""Shared request/response conventions for payroll schemas.

Write models reject unknown fields so immutable identifiers cannot be changed
through an update payload. Decimal public fields always serialize as strings
and months serialize as ``YYYY-MM``, matching the Basic Management and
Attendance API contracts.

Error-detail shapes live here because both the domain-error envelope and the
formula/calculation responses share them; later payroll slices may re-export
them from their feature modules.
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


class FormulaErrorPublic(SQLModel):
    """A formula detail error, carried only inside ``formula_errors[]``."""

    code: str
    message: str
    field_key: str | None = None
    position: int | None = None
    params: dict[str, Any] | None = None


class ConsistencyViolationPublic(SQLModel):
    """One failed category-anchored consistency check."""

    employee_id: uuid.UUID
    employee_no: str
    employee_name: str | None = None
    field_key: str
    check: str
    expected: str
    actual: str
