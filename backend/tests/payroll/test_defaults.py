"""System payroll defaults seeded by ``ensure_payroll_defaults``.

Expected field values come from the approved base fixture
``field-defs.json``, and the three numeric global values from
``global-params.json``. Tier amounts and keys come from the payroll
specification section 4.8 and the requirement policy text; tier labels and
display order are the product copy pinned by section 5.6.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, NamedTuple

from sqlmodel import Session, delete, select

from app.enums import PayrollGlobalParamType
from app.models import (
    PayrollConfigRevision,
    PayrollGlobalParam,
    SalaryFieldDef,
)
from app.services.payroll.defaults import ensure_payroll_defaults
from tests.utils.payroll_tables import truncate_payroll_system_tables

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_FIXTURES = REPO_ROOT / "docs" / "specs" / "payroll-golden-cases" / "base"


class ExpectedGlobalParam(NamedTuple):
    label: str
    category: str
    value_type: PayrollGlobalParamType
    display_order: int


EXPECTED_GLOBAL_PARAMS: dict[str, ExpectedGlobalParam] = {
    "tax_threshold": ExpectedGlobalParam(
        "个税起征点", "tax", PayrollGlobalParamType.NUMBER, 10
    ),
    "tax_rate": ExpectedGlobalParam(
        "预设个税税率", "tax", PayrollGlobalParamType.NUMBER, 20
    ),
    "social_rate": ExpectedGlobalParam(
        "社保费率（个人部分）", "social", PayrollGlobalParamType.NUMBER, 30
    ),
    "confidentiality_tier": ExpectedGlobalParam(
        "保密津贴档", "subsidy", PayrollGlobalParamType.JSON, 40
    ),
    "hightemp_tier": ExpectedGlobalParam(
        "高温津贴档", "subsidy", PayrollGlobalParamType.JSON, 50
    ),
    "tax_brackets": ExpectedGlobalParam(
        "个税税率表（预留）", "tax", PayrollGlobalParamType.JSON, 60
    ),
}

EXPECTED_CONFIDENTIALITY_TIERS = [
    {"level": 5, "label": "高层", "amount": 5000},
    {"level": 4, "label": "中层", "amount": 2000},
    {"level": 3, "label": "集团总部基层", "amount": 1000},
    {"level": 2, "label": "下属公司基层及关键涉密岗", "amount": 500},
    {"level": 1, "label": "班长及一般涉密基层", "amount": 240},
]

EXPECTED_HIGHTEMP_TIERS = [
    {"key": "outdoor", "label": "户外露天", "amount": 300},
    {"key": "indoor", "label": "室内非露天高温", "amount": 150},
    {"key": "none", "label": "非高温", "amount": 0},
]


def _golden_fields() -> list[dict[str, Any]]:
    return json.loads((BASE_FIXTURES / "field-defs.json").read_text("utf-8"))["fields"]


def _golden_global_numbers() -> dict[str, Decimal]:
    raw = json.loads((BASE_FIXTURES / "global-params.json").read_text("utf-8"))
    return {key: Decimal(value) for key, value in raw.items()}


def _clear_system_tables(db: Session) -> None:
    truncate_payroll_system_tables(db)
    db.commit()


def _field_rows(db: Session) -> dict[str, SalaryFieldDef]:
    return {row.field_key: row for row in db.exec(select(SalaryFieldDef)).all()}


def test_ensure_payroll_defaults_seeds_the_32_system_fields(db: Session) -> None:
    _clear_system_tables(db)

    ensure_payroll_defaults(db)

    expected = _golden_fields()
    rows = _field_rows(db)
    assert len(rows) == 32
    assert set(rows) == {field["field_key"] for field in expected}
    for field in expected:
        row = rows[field["field_key"]]
        assert row.label == field["label"]
        assert row.category == field["category"]
        assert row.calc_mode == field["calc_mode"]
        assert row.source_key == field["source_key"]
        assert row.default_formula == field["default_formula"]
        fixed_value = field["fixed_value"]
        assert row.fixed_value == (
            Decimal(fixed_value) if fixed_value is not None else None
        )
        assert row.display_order == field["display_order"]
        assert row.visible is field["visible"]
        assert row.is_system is field["is_system"]
        assert row.is_active is field["is_active"]


def test_ensure_payroll_defaults_seeds_the_six_global_parameters(
    db: Session,
) -> None:
    _clear_system_tables(db)

    ensure_payroll_defaults(db)

    rows = {row.key: row for row in db.exec(select(PayrollGlobalParam)).all()}
    assert len(rows) == 6
    assert set(rows) == set(EXPECTED_GLOBAL_PARAMS)
    for key, expected in EXPECTED_GLOBAL_PARAMS.items():
        row = rows[key]
        assert row.label == expected.label
        assert row.category == expected.category
        assert row.value_type == expected.value_type
        assert row.display_order == expected.display_order
        assert row.is_active is True
        assert (row.numeric_value is None) is (
            expected.value_type is PayrollGlobalParamType.JSON
        )
        assert (row.json_value is None) is (
            expected.value_type is PayrollGlobalParamType.NUMBER
        )

    numbers = _golden_global_numbers()
    assert numbers.keys() == {
        "tax_threshold",
        "tax_rate",
        "social_rate",
    }
    for key, value in numbers.items():
        assert rows[key].numeric_value == value

    assert rows["confidentiality_tier"].json_value == EXPECTED_CONFIDENTIALITY_TIERS
    assert rows["hightemp_tier"].json_value == EXPECTED_HIGHTEMP_TIERS
    assert rows["tax_brackets"].json_value == []


def test_ensure_payroll_defaults_is_idempotent_and_never_overwrites(
    db: Session,
) -> None:
    _clear_system_tables(db)
    ensure_payroll_defaults(db)

    field = db.exec(
        select(SalaryFieldDef).where(SalaryFieldDef.field_key == "base_pay")
    ).one()
    field.label = "自定义基本工资"
    field.default_formula = "0"
    field.visible = False
    param = db.exec(
        select(PayrollGlobalParam).where(PayrollGlobalParam.key == "tax_threshold")
    ).one()
    param.label = "自定义起征点"
    param.numeric_value = Decimal("6000")
    db.add(field)
    db.add(param)
    db.commit()

    ensure_payroll_defaults(db)

    assert len(db.exec(select(SalaryFieldDef)).all()) == 32
    assert len(db.exec(select(PayrollGlobalParam)).all()) == 6
    assert db.exec(select(PayrollConfigRevision)).all() == []

    db.refresh(field)
    db.refresh(param)
    assert field.label == "自定义基本工资"
    assert field.default_formula == "0"
    assert field.visible is False
    assert param.label == "自定义起征点"
    assert param.numeric_value == Decimal("6000")


def test_ensure_payroll_defaults_restores_only_missing_rows(db: Session) -> None:
    _clear_system_tables(db)
    ensure_payroll_defaults(db)

    db.exec(
        delete(SalaryFieldDef).where(SalaryFieldDef.field_key.in_(["base_pay", "net"]))
    )
    db.exec(
        delete(PayrollGlobalParam).where(
            PayrollGlobalParam.key.in_(["tax_rate", "hightemp_tier"])
        )
    )
    edited = db.exec(
        select(PayrollGlobalParam).where(PayrollGlobalParam.key == "social_rate")
    ).one()
    edited.numeric_value = Decimal("0.2")
    db.add(edited)
    db.commit()

    ensure_payroll_defaults(db)

    fields = _field_rows(db)
    params = {row.key: row for row in db.exec(select(PayrollGlobalParam)).all()}
    assert len(fields) == 32
    assert len(params) == 6
    golden = {field["field_key"]: field for field in _golden_fields()}
    for key in ("base_pay", "net"):
        assert fields[key].label == golden[key]["label"]
        assert fields[key].default_formula == golden[key]["default_formula"]
    assert params["tax_rate"].numeric_value == Decimal("0.03")
    assert params["hightemp_tier"].json_value == EXPECTED_HIGHTEMP_TIERS
    assert params["social_rate"].numeric_value == Decimal("0.2")
