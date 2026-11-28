"""System-owned payroll defaults seeded at startup.

The field catalog mirrors
``docs/specs/payroll-golden-cases/base/field-defs.json``. Rows are insert-only:
an existing row, including a user edit, is never updated or replaced. Default
formula upgrades therefore require an explicit later action, not a restart.
"""

import uuid
from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any, TypedDict

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session

from app.enums import (
    PayrollGlobalParamType,
    SalaryFieldCalcMode,
    SalaryFieldCategory,
)
from app.models import PayrollGlobalParam, SalaryFieldDef, get_datetime_utc


class _SalaryFieldDefault(TypedDict):
    field_key: str
    label: str
    category: SalaryFieldCategory
    calc_mode: SalaryFieldCalcMode
    source_key: str | None
    default_formula: str | None
    display_order: int


class _GlobalParamDefault(TypedDict):
    key: str
    label: str
    category: str
    value_type: PayrollGlobalParamType
    numeric_value: Decimal | None
    json_value: Any
    display_order: int


SYSTEM_SALARY_FIELDS: tuple[_SalaryFieldDefault, ...] = (
    {
        "field_key": "base_pay",
        "label": "基本工资(实)",
        "category": SalaryFieldCategory.EARNING,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": "ROUND(base_salary / weekday_full * weekday_attended, 2)",
        "display_order": 10,
    },
    {
        "field_key": "hightemp",
        "label": "高温补贴(实)",
        "category": SalaryFieldCategory.EARNING,
        "calc_mode": SalaryFieldCalcMode.PLAN,
        "source_key": "hightemp_subsidy",
        "default_formula": None,
        "display_order": 20,
    },
    {
        "field_key": "performance",
        "label": "绩效(实)",
        "category": SalaryFieldCategory.EARNING,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": (
            "ROUND(performance_salary - total_package / (weekday_full + "
            "weekend_full) * ((weekday_full + weekend_full) - weekday_attended - "
            "weekend_attended) + (base_salary - base_pay) + (overtime_pay - "
            "overtime_pay_actual), 2)"
        ),
        "display_order": 30,
    },
    {
        "field_key": "overtime_pay_actual",
        "label": "加班费(实)",
        "category": SalaryFieldCategory.EARNING,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": "ROUND(overtime_pay / weekend_full * weekend_attended, 2)",
        "display_order": 40,
    },
    {
        "field_key": "confidential",
        "label": "保密津贴(实)",
        "category": SalaryFieldCategory.EARNING,
        "calc_mode": SalaryFieldCalcMode.PLAN,
        "source_key": "confidentiality_allowance",
        "default_formula": None,
        "display_order": 50,
    },
    {
        "field_key": "social_sub",
        "label": "社保补贴(实)",
        "category": SalaryFieldCategory.EARNING,
        "calc_mode": SalaryFieldCalcMode.PLAN,
        "source_key": "social_subsidy",
        "default_formula": None,
        "display_order": 60,
    },
    {
        "field_key": "noncompete_sub",
        "label": "竞业补贴(实)",
        "category": SalaryFieldCategory.EARNING,
        "calc_mode": SalaryFieldCalcMode.PLAN,
        "source_key": "noncompete_subsidy",
        "default_formula": None,
        "display_order": 70,
    },
    {
        "field_key": "normal_pay",
        "label": "正常出勤工资",
        "category": SalaryFieldCategory.TOTAL,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": (
            "ROUND(base_pay + hightemp + performance + overtime_pay_actual + "
            "confidential + social_sub + noncompete_sub, 2)"
        ),
        "display_order": 80,
    },
    {
        "field_key": "paid_leave_pay",
        "label": "带薪假工资",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": "ROUND(base_salary / {avg_pay_days} * paid_leave_days, 2)",
        "display_order": 90,
    },
    {
        "field_key": "ot_subsidy",
        "label": "加班补贴",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": (
            "ROUND(base_salary / {avg_pay_days} / {work_hours} * "
            "{ot_mult_weekday} * ot_weekday_hours + base_salary / {avg_pay_days} / "
            "{work_hours} * {ot_mult_weekend} * ot_weekend_hours + base_salary / "
            "{avg_pay_days} / {work_hours} * {ot_mult_holiday} * ot_holiday_hours, 2)"
        ),
        "display_order": 100,
    },
    {
        "field_key": "phone_allowance",
        "label": "话费",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "phone_allowance",
        "default_formula": None,
        "display_order": 110,
    },
    {
        "field_key": "car_allowance",
        "label": "车补",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "car_allowance",
        "default_formula": None,
        "display_order": 120,
    },
    {
        "field_key": "other_addon",
        "label": "其他",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "other_addon",
        "default_formula": None,
        "display_order": 130,
    },
    {
        "field_key": "production_bonus",
        "label": "生产奖",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "production_bonus",
        "default_formula": None,
        "display_order": 140,
    },
    {
        "field_key": "commission",
        "label": "提成",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "commission",
        "default_formula": None,
        "display_order": 150,
    },
    {
        "field_key": "attendance_deduct",
        "label": "考勤扣款",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "attendance_deduct",
        "default_formula": None,
        "display_order": 160,
    },
    {
        "field_key": "admin_deduct",
        "label": "行政扣减",
        "category": SalaryFieldCategory.ADDON,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "admin_deduct",
        "default_formula": None,
        "display_order": 170,
    },
    {
        "field_key": "addon_sum",
        "label": "加减项小计",
        "category": SalaryFieldCategory.TOTAL,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": (
            "ROUND(SUM(paid_leave_pay, ot_subsidy, phone_allowance, car_allowance, "
            "other_addon, production_bonus, commission, attendance_deduct, "
            "admin_deduct), 2)"
        ),
        "display_order": 180,
    },
    {
        "field_key": "gross",
        "label": "应发工资",
        "category": SalaryFieldCategory.TOTAL,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": "ROUND(normal_pay + addon_sum, 2)",
        "display_order": 190,
    },
    {
        "field_key": "social_this",
        "label": "本期社保",
        "category": SalaryFieldCategory.DEDUCTION,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "social_this",
        "default_formula": None,
        "display_order": 200,
    },
    {
        "field_key": "tax",
        "label": "本期个税",
        "category": SalaryFieldCategory.DEDUCTION,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "tax",
        "default_formula": None,
        "display_order": 210,
    },
    {
        "field_key": "paid_advance",
        "label": "已发",
        "category": SalaryFieldCategory.DEDUCTION,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "paid_advance",
        "default_formula": None,
        "display_order": 220,
    },
    {
        "field_key": "deduct_sum",
        "label": "扣减项小计",
        "category": SalaryFieldCategory.TOTAL,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": "ROUND(SUM(social_this, tax, paid_advance), 2)",
        "display_order": 230,
    },
    {
        "field_key": "net",
        "label": "实发工资",
        "category": SalaryFieldCategory.TOTAL,
        "calc_mode": SalaryFieldCalcMode.FORMULA,
        "source_key": None,
        "default_formula": "ROUND(gross + deduct_sum, 2)",
        "display_order": 240,
    },
    {
        "field_key": "weekday_full",
        "label": "工作日满勤",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "weekday_full",
        "default_formula": None,
        "display_order": 250,
    },
    {
        "field_key": "weekend_full",
        "label": "周末满勤",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "weekend_full",
        "default_formula": None,
        "display_order": 260,
    },
    {
        "field_key": "weekday_attended",
        "label": "工作日出勤",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "weekday_attended",
        "default_formula": None,
        "display_order": 270,
    },
    {
        "field_key": "weekend_attended",
        "label": "周末出勤",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "weekend_attended",
        "default_formula": None,
        "display_order": 280,
    },
    {
        "field_key": "paid_leave_days",
        "label": "带薪假天数",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "paid_leave_days",
        "default_formula": None,
        "display_order": 290,
    },
    {
        "field_key": "ot_weekday_hours",
        "label": "工作日加班(小时)",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "ot_weekday_hours",
        "default_formula": None,
        "display_order": 300,
    },
    {
        "field_key": "ot_weekend_hours",
        "label": "周末加班(小时)",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "ot_weekend_hours",
        "default_formula": None,
        "display_order": 310,
    },
    {
        "field_key": "ot_holiday_hours",
        "label": "节假日加班(小时)",
        "category": SalaryFieldCategory.REFERENCE,
        "calc_mode": SalaryFieldCalcMode.IMPORT,
        "source_key": "ot_holiday_hours",
        "default_formula": None,
        "display_order": 320,
    },
)


# Confidentiality tier labels and amounts come from the payroll policy text in
# the requirement (five tiers); levels 5..1 follow employee.confidentiality_level,
# where 5 is the highest tier. High-temperature tier labels and amounts follow
# the same policy section. The tax bracket table is a reserved empty reference
# because section 4.8 fixes no bracket values for V1.
SYSTEM_GLOBAL_PARAMS: tuple[_GlobalParamDefault, ...] = (
    {
        "key": "tax_threshold",
        "label": "个税起征点",
        "category": "tax",
        "value_type": PayrollGlobalParamType.NUMBER,
        "numeric_value": Decimal("5000"),
        "json_value": None,
        "display_order": 10,
    },
    {
        "key": "tax_rate",
        "label": "预设个税税率",
        "category": "tax",
        "value_type": PayrollGlobalParamType.NUMBER,
        "numeric_value": Decimal("0.03"),
        "json_value": None,
        "display_order": 20,
    },
    {
        "key": "social_rate",
        "label": "社保费率（个人部分）",
        "category": "social",
        "value_type": PayrollGlobalParamType.NUMBER,
        "numeric_value": Decimal("0.23338"),
        "json_value": None,
        "display_order": 30,
    },
    {
        "key": "confidentiality_tier",
        "label": "保密津贴档",
        "category": "subsidy",
        "value_type": PayrollGlobalParamType.JSON,
        "numeric_value": None,
        "json_value": [
            {"level": 5, "label": "高层", "amount": 5000},
            {"level": 4, "label": "中层", "amount": 2000},
            {"level": 3, "label": "集团总部基层", "amount": 1000},
            {"level": 2, "label": "下属公司基层及关键涉密岗", "amount": 500},
            {"level": 1, "label": "班长及一般涉密基层", "amount": 240},
        ],
        "display_order": 40,
    },
    {
        "key": "hightemp_tier",
        "label": "高温津贴档",
        "category": "subsidy",
        "value_type": PayrollGlobalParamType.JSON,
        "numeric_value": None,
        "json_value": [
            {"key": "outdoor", "label": "户外露天", "amount": 300},
            {"key": "indoor", "label": "室内非露天高温", "amount": 150},
            {"key": "none", "label": "非高温", "amount": 0},
        ],
        "display_order": 50,
    },
    {
        "key": "tax_brackets",
        "label": "个税税率表（预留）",
        "category": "tax",
        "value_type": PayrollGlobalParamType.JSON,
        "numeric_value": None,
        "json_value": [],
        "display_order": 60,
    },
)


def _stamp_rows(
    templates: Iterable[Mapping[str, Any]], **columns: Any
) -> list[dict[str, Any]]:
    now = get_datetime_utc()
    return [
        {
            **template,
            "id": uuid.uuid7(),
            "created_at": now,
            "updated_at": now,
            **columns,
        }
        for template in templates
    ]


def _system_field_rows() -> list[dict[str, Any]]:
    return _stamp_rows(
        SYSTEM_SALARY_FIELDS, visible=True, is_system=True, is_active=True
    )


def _system_global_rows() -> list[dict[str, Any]]:
    return _stamp_rows(SYSTEM_GLOBAL_PARAMS, is_active=True)


def ensure_payroll_defaults(session: Session) -> None:
    """Insert missing system-owned payroll defaults.

    Existing rows win: conflicts are ignored rather than updated, so a restart
    never overwrites an administrator's edits.
    """
    session.exec(
        insert(SalaryFieldDef).values(_system_field_rows()).on_conflict_do_nothing()
    )
    session.exec(
        insert(PayrollGlobalParam)
        .values(_system_global_rows())
        .on_conflict_do_nothing()
    )
    session.commit()
