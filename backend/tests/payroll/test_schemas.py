"""Payroll schema package: shared conventions for requests and responses."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas_payroll.common import (
    ConsistencyViolationPublic,
    DecimalString,
    FormulaErrorPublic,
    MonthString,
    ReadModel,
    WriteModel,
)


class _SampleWrite(WriteModel):
    month: MonthString
    amount: DecimalString


class _SampleRead(ReadModel):
    id: uuid.UUID
    label: str


def test_write_models_forbid_unknown_fields() -> None:
    with pytest.raises(ValidationError) as error:
        _SampleWrite(month="2026-09", amount="1.00", extra_field=True)

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_month_string_serializes_as_year_month() -> None:
    model = _SampleWrite(month="2026-09", amount="1.00")

    assert model.model_dump(mode="json")["month"] == "2026-09"


def test_month_string_accepts_stored_first_of_month_dates() -> None:
    model = _SampleWrite(month=date(2026, 9, 1), amount="1.00")

    assert model.month == "2026-09"


@pytest.mark.parametrize("invalid_month", ["2026-13", "0000-01", "２０２６-０９"])
def test_month_string_rejects_invalid_months(invalid_month: str) -> None:
    with pytest.raises(ValidationError):
        _SampleWrite(month=invalid_month, amount="1.00")


def test_decimal_values_serialize_as_strings() -> None:
    model = _SampleWrite(month="2026-09", amount=Decimal("1234.50"))

    assert model.model_dump(mode="json")["amount"] == "1234.50"
    assert model.model_dump_json().find('"amount":"1234.50"') >= 0


def test_read_models_load_from_attributes() -> None:
    class _Row:
        id = uuid.uuid7()
        label = "基本工资"

    row = _SampleRead.model_validate(_Row())

    assert row.label == "基本工资"


def test_formula_error_public_shape() -> None:
    error = FormulaErrorPublic(
        code="formula_unknown_field",
        message="公式引用了未知字段",
        field_key="net",
        position=3,
        params={"name": "unknown"},
    )

    dumped = error.model_dump(mode="json")

    assert dumped["code"] == "formula_unknown_field"
    assert dumped["field_key"] == "net"
    assert dumped["params"] == {"name": "unknown"}


def test_consistency_violation_public_shape() -> None:
    employee_id = uuid.uuid7()
    violation = ConsistencyViolationPublic(
        employee_id=employee_id,
        employee_no="E001",
        employee_name="张三",
        field_key="net",
        check="net",
        expected="5000.00",
        actual="4900.00",
    )

    dumped = violation.model_dump(mode="json")

    assert dumped["employee_id"] == str(employee_id)
    assert dumped["expected"] == "5000.00"
    assert dumped["actual"] == "4900.00"


def test_shared_types_can_be_imported_from_the_package() -> None:
    from app.schemas_payroll import common

    assert common.WriteModel is WriteModel
    assert common.DecimalString is DecimalString
    assert common.MonthString is MonthString


def test_write_models_dump_only_declared_fields() -> None:
    model = _SampleWrite(month="2026-09", amount="0")
    payload: dict[str, Any] = model.model_dump(mode="json")

    assert payload == {"month": "2026-09", "amount": "0"}
