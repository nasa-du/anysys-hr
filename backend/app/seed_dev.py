"""Development-only generated seed data.

Run manually from the backend directory with ``uv run python -m app.seed_dev``.
The script refuses to run unless ``FASTAPI_ENV=development`` and only inserts
rows that are missing by business code, so user edits are never overwritten.

The dataset is deterministic: a fixed random seed drives every generated row,
and the same scale always produces exactly the same companies, org trees,
employees, rosters, imports, and calculation results.

Three mid-sized companies are seeded:

* ``C1`` 华信建设 — full organization tree with an inactive department and an
  inactive cost center.
* ``C2`` 云启科技 — technology company with a nested department tree.
* ``C3`` 明德考勤演示 — the attendance demo company. Attendance data covers
  2026-08, 2026-09, and 2026-10 at full depth: plans, expanded rosters, punch
  and OA imports committed through the real service path, and pre-calculated
  monthly results. ``C1`` and ``C2`` never receive attendance rows.

One fixed payroll company is also seeded:

* ``C4`` 明德薪资演示 — the payroll demo skeleton: 7 departments, 6 positions,
  6 cost centers, and exactly 15 employees with the documented edge cases
  (duplicate names, a resigned employee, a probation hire, a future hire, and
  an unassigned cost center). Phase 0 adds no payroll configuration or
  results; later payroll slices complete this company through the real
  service paths.

``FULL_SCALE`` is what ``main()`` seeds; ``SMALL_SCALE`` keeps the same code
paths at a size that is cheap enough for the test suite. Both scales contain
``C4`` at exactly 15 employees.
"""

import calendar
import csv
import io
import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.core.security import get_password_hash
from app.enums import (
    AttendanceMonthStatus,
    CalcRunStatus,
    ContractType,
    EmployeeStatus,
    Gender,
    HolidayDayType,
    ImportBatchStatus,
    ImportDataType,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import (
    AttendanceMonth,
    AttendanceRule,
    CalcRun,
    Company,
    CostCenter,
    Department,
    Employee,
    Holiday,
    ImportBatch,
    ImportMappingTemplate,
    PlanDay,
    PlanRuleOverride,
    PlanScope,
    Position,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
    User,
)
from app.services.attendance import expansion, imports
from app.services.attendance import months as month_service

logger = logging.getLogger(__name__)

SEED_RANDOM_SEED = 20261116
USER_PASSWORD = "changethis"
ATTENDANCE_MONTHS: tuple[date, ...] = (
    date(2026, 8, 1),
    date(2026, 9, 1),
    date(2026, 10, 1),
)


@dataclass(frozen=True)
class SeedScale:
    """Employee headcount per company for one seed run."""

    name: str
    employees: dict[str, int]


FULL_SCALE = SeedScale("full", {"C1": 240, "C2": 420, "C3": 520, "C4": 15})
SMALL_SCALE = SeedScale("small", {"C1": 18, "C2": 16, "C3": 24, "C4": 15})

# The payroll demo company's organization is fixed, not generated.
PAYROLL_COMPANY_CODE = "C4"


COMPANIES: list[dict[str, Any]] = [
    {"company_code": "C1", "company_name": "华信建设", "note": "中型组织示例"},
    {
        "company_code": "C2",
        "company_name": "云启科技",
        "note": "中型组织示例，研发团队为主",
    },
    {
        "company_code": "C3",
        "company_name": "明德考勤演示",
        "note": "考勤演示公司；C1-C2 不包含考勤数据",
    },
    {
        "company_code": PAYROLL_COMPANY_CODE,
        "company_name": "明德薪资演示",
        "note": "薪资演示公司；仅包含组织与员工骨架，不含薪资结果",
    },
]

USERS: list[tuple[str, str]] = [
    ("c1.hr@example.com", "华信人力资源"),
    ("c1.manager@example.com", "华信生产经理"),
    ("c2.hr@example.com", "云启人力资源"),
    ("c2.admin@example.com", "云启行政主管"),
    ("c3.hr@example.com", "明德人力资源"),
    ("c3.payroll@example.com", "明德薪酬专员"),
    ("auditor@example.com", "审计专员"),
    ("viewer@example.com", "演示访客"),
    ("ops@example.com", "运维管理员"),
]


# C4 is the payroll demo company. These rows are fixed (not generated) so the
# documented edge cases survive every scale: duplicate names, a resigned
# employee, a probation hire, a future hire, and an unassigned cost center.
C4_EMPLOYEES: list[dict[str, Any]] = [
    {
        "employee_no": "E4001",
        "name": "冯芷茵",
        "dept_code": "PROD-W1",
        "position_code": "POS-OP",
        "cost_org_code": "CC-MINE",
        "hire_date": date(2020, 4, 11),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4002",
        "name": "刘衍英",
        "dept_code": "FIN",
        "position_code": "POS-ACC",
        "cost_org_code": "CC-ADMIN",
        "hire_date": date(2018, 9, 3),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4003",
        "name": "周玉琼",
        "dept_code": "PROD-W1",
        "position_code": "POS-OP",
        "cost_org_code": "CC-MINE",
        "hire_date": date(2019, 3, 18),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4004",
        "name": "胡国邵",
        "dept_code": "PROD-W1",
        "position_code": "POS-OP",
        "cost_org_code": "CC-MINE",
        "hire_date": date(2017, 6, 1),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4005",
        "name": "李金辉",
        "dept_code": "PROD-W2",
        "position_code": "POS-OP",
        "cost_org_code": "CC-SMELT",
        "hire_date": date(2021, 11, 8),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4006",
        "name": "黄佳誉",
        "dept_code": "TECH",
        "position_code": "POS-TECH",
        "cost_org_code": "CC-TECH",
        "hire_date": date(2020, 2, 17),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4007",
        "name": "梁林高",
        "dept_code": "ADMIN",
        "position_code": "POS-ADMIN",
        "cost_org_code": "CC-ADMIN",
        "hire_date": date(2016, 5, 23),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4008",
        "name": "黄国锋",
        "dept_code": "PROD-W2",
        "position_code": "POS-LEAD",
        "cost_org_code": "CC-SMELT",
        "hire_date": date(2019, 8, 30),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4009",
        "name": "申佳林",
        "dept_code": "ADMIN",
        "position_code": "POS-ADMIN",
        "cost_org_code": "CC-ADMIN",
        "hire_date": date(2015, 10, 12),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4010",
        "name": "张伟",
        "dept_code": "PROD-W1",
        "position_code": "POS-OP",
        "cost_org_code": None,
        "hire_date": date(2019, 1, 1),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4011",
        "name": "张伟",
        "dept_code": "FIN",
        "position_code": "POS-ACC",
        "cost_org_code": "CC-ADMIN",
        "hire_date": date(2020, 1, 1),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4012",
        "name": "王强",
        "dept_code": "PROD-W1",
        "position_code": "POS-OP",
        "cost_org_code": "CC-MINE",
        "hire_date": date(2018, 1, 1),
        "resign_date": date(2026, 8, 31),
        "status": EmployeeStatus.RESIGNED,
    },
    {
        "employee_no": "E4013",
        "name": "李娜",
        "dept_code": "PROD-W2",
        "position_code": "POS-OP",
        "cost_org_code": "CC-SMELT",
        "hire_date": date(2026, 9, 15),
        "status": EmployeeStatus.PROBATION,
    },
    {
        "employee_no": "E4014",
        "name": "赵志强",
        "dept_code": "ADMIN",
        "position_code": "POS-DRIVER",
        "cost_org_code": "CC-ADMIN",
        "hire_date": date(2026, 12, 1),
        "status": EmployeeStatus.ACTIVE,
    },
    {
        "employee_no": "E4015",
        "name": "陈晓",
        "dept_code": "TECH",
        "position_code": "POS-TECH",
        "cost_org_code": "CC-TECH",
        "hire_date": date(2021, 7, 19),
        "status": EmployeeStatus.ACTIVE,
    },
]


# Parents are listed before their children so one pass can resolve every
# ``parent_code`` to the row inserted earlier in the same run. The skeleton
# codes keep the documented demo scenarios; the generated ones add realistic
# breadth at mid-sized scale.
DEPARTMENTS: list[dict[str, Any]] = [
    # C1 华信建设
    {
        "company_code": "C1",
        "dept_code": "D1",
        "dept_name": "总部",
        "parent_code": None,
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "dept_code": "D2",
        "dept_name": "生产部",
        "parent_code": "D1",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "dept_code": "D3",
        "dept_name": "一车间",
        "parent_code": "D2",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "dept_code": "D4",
        "dept_name": "二车间",
        "parent_code": "D2",
        "order_no": 1,
    },
    {
        "company_code": "C1",
        "dept_code": "D5",
        "dept_name": "运营部",
        "parent_code": "D1",
        "order_no": 1,
    },
    {
        "company_code": "C1",
        "dept_code": "D6",
        "dept_name": "财务部",
        "parent_code": "D1",
        "order_no": 2,
    },
    # Inactive department without active employee references, used to
    # demonstrate the inactive state; keep seeded employees elsewhere.
    {
        "company_code": "C1",
        "dept_code": "D7",
        "dept_name": "旧项目部",
        "parent_code": "D1",
        "order_no": 9,
        "is_active": False,
    },
    {
        "company_code": "C1",
        "dept_code": "D8",
        "dept_name": "三车间",
        "parent_code": "D2",
        "order_no": 2,
    },
    {
        "company_code": "C1",
        "dept_code": "D9",
        "dept_name": "四车间",
        "parent_code": "D2",
        "order_no": 3,
    },
    {
        "company_code": "C1",
        "dept_code": "D10",
        "dept_name": "质检部",
        "parent_code": "D1",
        "order_no": 3,
    },
    {
        "company_code": "C1",
        "dept_code": "D11",
        "dept_name": "仓储部",
        "parent_code": "D1",
        "order_no": 4,
    },
    {
        "company_code": "C1",
        "dept_code": "D12",
        "dept_name": "人力资源部",
        "parent_code": "D1",
        "order_no": 5,
    },
    {
        "company_code": "C1",
        "dept_code": "D13",
        "dept_name": "采购部",
        "parent_code": "D1",
        "order_no": 6,
    },
    # C2 云启科技
    {
        "company_code": "C2",
        "dept_code": "K1",
        "dept_name": "总部",
        "parent_code": None,
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "dept_code": "K2",
        "dept_name": "研发部",
        "parent_code": "K1",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "dept_code": "K3",
        "dept_name": "市场部",
        "parent_code": "K1",
        "order_no": 1,
    },
    {
        "company_code": "C2",
        "dept_code": "K4",
        "dept_name": "产品部",
        "parent_code": "K1",
        "order_no": 2,
    },
    {
        "company_code": "C2",
        "dept_code": "K5",
        "dept_name": "运维部",
        "parent_code": "K1",
        "order_no": 3,
    },
    {
        "company_code": "C2",
        "dept_code": "K6",
        "dept_name": "客服部",
        "parent_code": "K1",
        "order_no": 4,
    },
    {
        "company_code": "C2",
        "dept_code": "K7",
        "dept_name": "财务部",
        "parent_code": "K1",
        "order_no": 5,
    },
    {
        "company_code": "C2",
        "dept_code": "K8",
        "dept_name": "人力资源部",
        "parent_code": "K1",
        "order_no": 6,
    },
    {
        "company_code": "C2",
        "dept_code": "K9",
        "dept_name": "测试部",
        "parent_code": "K2",
        "order_no": 0,
    },
    # C3 明德考勤演示（考勤种子数据只写 C3）
    {
        "company_code": "C3",
        "dept_code": "D1",
        "dept_name": "生产部",
        "parent_code": None,
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "dept_code": "D2",
        "dept_name": "财务部",
        "parent_code": None,
        "order_no": 1,
    },
    {
        "company_code": "C3",
        "dept_code": "D3",
        "dept_name": "技术部",
        "parent_code": None,
        "order_no": 2,
    },
    {
        "company_code": "C3",
        "dept_code": "D4",
        "dept_name": "行政部",
        "parent_code": None,
        "order_no": 3,
    },
    {
        "company_code": "C3",
        "dept_code": "D5",
        "dept_name": "一车间",
        "parent_code": "D1",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "dept_code": "D6",
        "dept_name": "二车间",
        "parent_code": "D1",
        "order_no": 1,
    },
    {
        "company_code": "C3",
        "dept_code": "D7",
        "dept_name": "三车间",
        "parent_code": "D1",
        "order_no": 2,
    },
    {
        "company_code": "C3",
        "dept_code": "D8",
        "dept_name": "质检组",
        "parent_code": "D1",
        "order_no": 3,
    },
    {
        "company_code": "C3",
        "dept_code": "D9",
        "dept_name": "仓储组",
        "parent_code": "D1",
        "order_no": 4,
    },
    {
        "company_code": "C3",
        "dept_code": "D10",
        "dept_name": "研发一组",
        "parent_code": "D3",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "dept_code": "D11",
        "dept_name": "研发二组",
        "parent_code": "D3",
        "order_no": 1,
    },
    {
        "company_code": "C3",
        "dept_code": "D12",
        "dept_name": "后勤组",
        "parent_code": "D4",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "dept_code": "D13",
        "dept_name": "人力资源部",
        "parent_code": None,
        "order_no": 4,
    },
    # C4 明德薪资演示（薪资演示骨架，D4 切片补齐配置与结果）
    {
        "company_code": "C4",
        "dept_code": "HQ",
        "dept_name": "总部",
        "parent_code": None,
        "order_no": 10,
    },
    {
        "company_code": "C4",
        "dept_code": "PROD",
        "dept_name": "生产部",
        "parent_code": "HQ",
        "order_no": 20,
    },
    {
        "company_code": "C4",
        "dept_code": "PROD-W1",
        "dept_name": "一车间",
        "parent_code": "PROD",
        "order_no": 10,
    },
    {
        "company_code": "C4",
        "dept_code": "PROD-W2",
        "dept_name": "二车间",
        "parent_code": "PROD",
        "order_no": 20,
    },
    {
        "company_code": "C4",
        "dept_code": "FIN",
        "dept_name": "财务部",
        "parent_code": "HQ",
        "order_no": 30,
    },
    {
        "company_code": "C4",
        "dept_code": "TECH",
        "dept_name": "技术部",
        "parent_code": "HQ",
        "order_no": 40,
    },
    {
        "company_code": "C4",
        "dept_code": "ADMIN",
        "dept_name": "行政部",
        "parent_code": "HQ",
        "order_no": 50,
    },
]


# Relative headcount weights per department. ``_allocate_counts`` scales them
# to the active scale so the full run lands on the documented totals.
DEPT_WEIGHTS: dict[str, dict[str, int]] = {
    "C1": {
        "D1": 35,
        "D2": 20,
        "D3": 25,
        "D4": 25,
        "D5": 20,
        "D6": 15,
        "D8": 25,
        "D9": 25,
        "D10": 15,
        "D11": 15,
        "D12": 10,
        "D13": 10,
    },
    "C2": {
        "K1": 40,
        "K2": 90,
        "K3": 60,
        "K4": 50,
        "K5": 50,
        "K6": 60,
        "K7": 25,
        "K8": 20,
        "K9": 25,
    },
    "C3": {
        "D1": 95,
        "D2": 35,
        "D3": 55,
        "D4": 30,
        "D5": 55,
        "D6": 55,
        "D7": 45,
        "D8": 35,
        "D9": 30,
        "D10": 25,
        "D11": 25,
        "D12": 20,
        "D13": 15,
    },
}


# Positions are company-level and reference their default department by code.
POSITIONS: list[dict[str, Any]] = [
    {
        "company_code": "C1",
        "position_code": "P1",
        "position_name": "项目经理",
        "dept_code": "D5",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P2",
        "position_name": "生产主管",
        "dept_code": "D2",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P3",
        "position_name": "车间工人",
        "dept_code": "D3",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P4",
        "position_name": "财务会计",
        "dept_code": "D6",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P5",
        "position_name": "运营专员",
        "dept_code": "D5",
        "order_no": 1,
    },
    # No default department: the employee form must not prefill one.
    {
        "company_code": "C1",
        "position_code": "P6",
        "position_name": "行政专员",
        "dept_code": None,
        "order_no": 2,
    },
    {
        "company_code": "C1",
        "position_code": "P7",
        "position_name": "质检员",
        "dept_code": "D10",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P8",
        "position_name": "仓储管理员",
        "dept_code": "D11",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P9",
        "position_name": "招聘专员",
        "dept_code": "D12",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P10",
        "position_name": "采购专员",
        "dept_code": "D13",
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "position_code": "P11",
        "position_name": "设备维修工",
        "dept_code": "D2",
        "order_no": 1,
    },
    {
        "company_code": "C1",
        "position_code": "P12",
        "position_name": "人力资源经理",
        "dept_code": "D12",
        "order_no": 1,
    },
    {
        "company_code": "C2",
        "position_code": "K1",
        "position_name": "研发工程师",
        "dept_code": "K2",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K2",
        "position_name": "市场专员",
        "dept_code": "K3",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K3",
        "position_name": "产品经理",
        "dept_code": "K4",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K4",
        "position_name": "运维工程师",
        "dept_code": "K5",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K5",
        "position_name": "客服专员",
        "dept_code": "K6",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K6",
        "position_name": "会计",
        "dept_code": "K7",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K7",
        "position_name": "测试工程师",
        "dept_code": "K9",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K8",
        "position_name": "人力资源专员",
        "dept_code": "K8",
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "position_code": "K9",
        "position_name": "前端工程师",
        "dept_code": "K2",
        "order_no": 1,
    },
    {
        "company_code": "C2",
        "position_code": "K10",
        "position_name": "算法工程师",
        "dept_code": "K2",
        "order_no": 2,
    },
    {
        "company_code": "C3",
        "position_code": "P1",
        "position_name": "生产操作工",
        "dept_code": "D1",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P2",
        "position_name": "园林工",
        "dept_code": "D1",
        "order_no": 1,
    },
    {
        "company_code": "C3",
        "position_code": "P3",
        "position_name": "会计",
        "dept_code": "D2",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P4",
        "position_name": "技术员",
        "dept_code": "D3",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P5",
        "position_name": "行政专员",
        "dept_code": "D4",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P6",
        "position_name": "质检员",
        "dept_code": "D8",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P7",
        "position_name": "仓储管理员",
        "dept_code": "D9",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P8",
        "position_name": "研发工程师",
        "dept_code": "D10",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P9",
        "position_name": "后勤专员",
        "dept_code": "D12",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P10",
        "position_name": "财务主管",
        "dept_code": "D2",
        "order_no": 1,
    },
    {
        "company_code": "C3",
        "position_code": "P11",
        "position_name": "车间主任",
        "dept_code": "D5",
        "order_no": 0,
    },
    {
        "company_code": "C3",
        "position_code": "P12",
        "position_name": "人力资源专员",
        "dept_code": "D13",
        "order_no": 0,
    },
    # C4 薪资演示岗位；POS-DRIVER 在 D4 切片保持未配置以演示阻断。
    {
        "company_code": "C4",
        "position_code": "POS-LEAD",
        "position_name": "生产线班长",
        "dept_code": "PROD",
        "order_no": 10,
    },
    {
        "company_code": "C4",
        "position_code": "POS-OP",
        "position_name": "操作工",
        "dept_code": "PROD",
        "order_no": 20,
    },
    {
        "company_code": "C4",
        "position_code": "POS-ACC",
        "position_name": "会计",
        "dept_code": "FIN",
        "order_no": 30,
    },
    {
        "company_code": "C4",
        "position_code": "POS-TECH",
        "position_name": "技术员",
        "dept_code": "TECH",
        "order_no": 40,
    },
    {
        "company_code": "C4",
        "position_code": "POS-ADMIN",
        "position_name": "行政专员",
        "dept_code": "ADMIN",
        "order_no": 50,
    },
    {
        "company_code": "C4",
        "position_code": "POS-DRIVER",
        "position_name": "司机",
        "dept_code": "ADMIN",
        "order_no": 60,
    },
]


# Candidate positions per department, used to assign generated employees. The
# first candidate is the department lead's position; the remaining ones rotate.
DEPT_POSITIONS: dict[str, dict[str, list[str]]] = {
    "C1": {
        "D1": ["P1", "P6"],
        "D2": ["P2", "P11"],
        "D3": ["P3"],
        "D4": ["P3"],
        "D5": ["P5"],
        "D6": ["P4"],
        "D8": ["P3"],
        "D9": ["P3"],
        "D10": ["P7"],
        "D11": ["P8"],
        "D12": ["P9", "P12"],
        "D13": ["P10"],
    },
    "C2": {
        "K1": ["K8", "K6"],
        "K2": ["K1", "K9", "K10"],
        "K3": ["K2"],
        "K4": ["K3"],
        "K5": ["K4"],
        "K6": ["K5"],
        "K7": ["K6"],
        "K8": ["K8"],
        "K9": ["K7"],
    },
    "C3": {
        "D1": ["P1", "P2"],
        "D2": ["P3", "P10"],
        "D3": ["P4"],
        "D4": ["P5"],
        "D5": ["P1"],
        "D6": ["P1"],
        "D7": ["P1"],
        "D8": ["P6"],
        "D9": ["P7"],
        "D10": ["P8"],
        "D11": ["P8"],
        "D12": ["P9"],
        "D13": ["P12"],
    },
}


COST_CENTERS: list[dict[str, Any]] = [
    {
        "company_code": "C1",
        "cost_org_code": "K1",
        "cost_org_name": "总部成本中心",
        "parent_code": None,
        "budget": Decimal("5000000.00"),
        "warn_pct": 85,
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K2",
        "cost_org_name": "生产成本中心",
        "parent_code": "K1",
        "budget": Decimal("3200000.00"),
        "warn_pct": 90,
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K3",
        "cost_org_name": "一车间成本中心",
        "parent_code": "K2",
        "budget": Decimal("1800000.00"),
        "warn_pct": 95,
        "order_no": 0,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K4",
        "cost_org_name": "二车间成本中心",
        "parent_code": "K2",
        "budget": Decimal("1200000.00"),
        "warn_pct": 90,
        "order_no": 1,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K5",
        "cost_org_name": "运营成本中心",
        "parent_code": "K1",
        "budget": Decimal("800000.00"),
        "warn_pct": 85,
        "order_no": 1,
    },
    # Inactive cost center without active employee references, used to
    # demonstrate the inactive state; keep seeded employees elsewhere.
    {
        "company_code": "C1",
        "cost_org_code": "K6",
        "cost_org_name": "旧项目成本中心",
        "parent_code": "K1",
        "budget": Decimal("0.00"),
        "warn_pct": 80,
        "order_no": 9,
        "is_active": False,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K7",
        "cost_org_name": "三车间成本中心",
        "parent_code": "K2",
        "budget": Decimal("900000.00"),
        "warn_pct": 90,
        "order_no": 2,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K8",
        "cost_org_name": "四车间成本中心",
        "parent_code": "K2",
        "budget": Decimal("700000.00"),
        "warn_pct": 90,
        "order_no": 3,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K9",
        "cost_org_name": "质检成本中心",
        "parent_code": "K1",
        "budget": Decimal("500000.00"),
        "warn_pct": 85,
        "order_no": 2,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K10",
        "cost_org_name": "仓储成本中心",
        "parent_code": "K1",
        "budget": Decimal("450000.00"),
        "warn_pct": 85,
        "order_no": 3,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K11",
        "cost_org_name": "人力成本中心",
        "parent_code": "K1",
        "budget": Decimal("300000.00"),
        "warn_pct": 85,
        "order_no": 4,
    },
    {
        "company_code": "C1",
        "cost_org_code": "K12",
        "cost_org_name": "采购成本中心",
        "parent_code": "K1",
        "budget": Decimal("350000.00"),
        "warn_pct": 85,
        "order_no": 5,
    },
    {
        "company_code": "C2",
        "cost_org_code": "K1",
        "cost_org_name": "总部成本中心",
        "parent_code": None,
        "budget": Decimal("500000.00"),
        "warn_pct": 85,
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "cost_org_code": "K2",
        "cost_org_name": "研发成本中心",
        "parent_code": "K1",
        "budget": Decimal("300000.00"),
        "warn_pct": 90,
        "order_no": 0,
    },
    {
        "company_code": "C2",
        "cost_org_code": "K3",
        "cost_org_name": "市场成本中心",
        "parent_code": "K1",
        "budget": Decimal("200000.00"),
        "warn_pct": 85,
        "order_no": 1,
    },
    {
        "company_code": "C2",
        "cost_org_code": "K4",
        "cost_org_name": "运营成本中心",
        "parent_code": "K1",
        "budget": Decimal("150000.00"),
        "warn_pct": 85,
        "order_no": 2,
    },
    {
        "company_code": "C2",
        "cost_org_code": "K5",
        "cost_org_name": "客服成本中心",
        "parent_code": "K1",
        "budget": Decimal("100000.00"),
        "warn_pct": 85,
        "order_no": 3,
    },
    # C4 薪资演示成本中心；预算只在根节点计入公司预算。
    {
        "company_code": "C4",
        "cost_org_code": "CC-PROD",
        "cost_org_name": "生产成本中心",
        "parent_code": None,
        "budget": Decimal("100000.00"),
        "warn_pct": 90,
        "order_no": 10,
    },
    {
        "company_code": "C4",
        "cost_org_code": "CC-MINE",
        "cost_org_name": "采选成本中心",
        "parent_code": "CC-PROD",
        "budget": Decimal("20000.00"),
        "warn_pct": 90,
        "order_no": 10,
    },
    {
        "company_code": "C4",
        "cost_org_code": "CC-SMELT",
        "cost_org_name": "冶炼成本中心",
        "parent_code": "CC-PROD",
        "budget": Decimal("22000.00"),
        "warn_pct": 90,
        "order_no": 20,
    },
    {
        "company_code": "C4",
        "cost_org_code": "CC-TECH",
        "cost_org_name": "技术成本中心",
        "parent_code": None,
        "budget": Decimal("25000.00"),
        "warn_pct": 90,
        "order_no": 20,
    },
    {
        "company_code": "C4",
        "cost_org_code": "CC-ADMIN",
        "cost_org_name": "行政成本中心",
        "parent_code": None,
        "budget": Decimal("24000.00"),
        "warn_pct": 90,
        "order_no": 30,
    },
    {
        "company_code": "C4",
        "cost_org_code": "CC-EMPTY",
        "cost_org_name": "待启用成本中心",
        "parent_code": None,
        "budget": Decimal("0.00"),
        "warn_pct": 90,
        "order_no": 40,
    },
]


DEPT_COST_CENTER: dict[str, dict[str, str]] = {
    "C1": {
        "D1": "K1",
        "D2": "K2",
        "D3": "K3",
        "D4": "K4",
        "D5": "K5",
        "D6": "K1",
        "D8": "K7",
        "D9": "K8",
        "D10": "K9",
        "D11": "K10",
        "D12": "K11",
        "D13": "K12",
    },
    "C2": {
        "K1": "K1",
        "K2": "K2",
        "K3": "K3",
        "K4": "K4",
        "K5": "K4",
        "K6": "K5",
        "K7": "K1",
        "K8": "K1",
        "K9": "K2",
    },
}


SHIFTS: list[dict[str, Any]] = [
    {
        "company_code": "C3",
        "shift_code": "ADM",
        "shift_name": "行政班",
        "start_time": time(8, 30),
        "end_time": time(17, 30),
        "cross_day": False,
        "break_start": None,
        "break_end": None,
        "rest_minutes": 60,
        "color": "#2563EB",
    },
    {
        "company_code": "C3",
        "shift_code": "TEC",
        "shift_name": "技术员班",
        "start_time": time(8, 0),
        "end_time": time(18, 0),
        "cross_day": False,
        "break_start": None,
        "break_end": None,
        "rest_minutes": 60,
        "color": "#7C3AED",
    },
    {
        "company_code": "C3",
        "shift_code": "YL",
        "shift_name": "园林班",
        "start_time": time(7, 30),
        "end_time": time(17, 30),
        "cross_day": False,
        "break_start": time(11, 30),
        "break_end": time(13, 30),
        "rest_minutes": 120,
        "color": "#16A34A",
    },
    {
        "company_code": "C3",
        "shift_code": "EARLY",
        "shift_name": "早班",
        "start_time": time(6, 0),
        "end_time": time(14, 0),
        "cross_day": False,
        "break_start": None,
        "break_end": None,
        "rest_minutes": 60,
        "color": "#F59E0B",
    },
    {
        "company_code": "C3",
        "shift_code": "MID",
        "shift_name": "中班",
        "start_time": time(14, 0),
        "end_time": time(22, 0),
        "cross_day": False,
        "break_start": None,
        "break_end": None,
        "rest_minutes": 60,
        "color": "#0EA5E9",
    },
    {
        "company_code": "C3",
        "shift_code": "NIGHT",
        "shift_name": "夜班",
        "start_time": time(22, 0),
        "end_time": time(6, 0),
        "cross_day": True,
        "break_start": time(2, 0),
        "break_end": time(3, 0),
        "rest_minutes": 60,
        "color": "#1E293B",
    },
    {
        "company_code": "C3",
        "shift_code": "DAWN",
        "shift_name": "凌晨班",
        "start_time": time(2, 0),
        "end_time": time(10, 0),
        "cross_day": False,
        "break_start": None,
        "break_end": None,
        "rest_minutes": 60,
        "color": "#DC2626",
    },
]


ATTENDANCE_RULES: list[dict[str, Any]] = [
    {
        "company_code": "C3",
        "punch_window_min": 120,
        "late_cap_min": 240,
        "early_cap_min": 240,
        "ot_max_min": 600,
        "late_grace_min": 5,
        "early_grace_min": 5,
        "ot_threshold_min": 30,
        "absent_if_no_punch": True,
        "break_punch_required": True,
        "break_punch_tolerance_min": 60,
        "absent_deduct_per_day": Decimal("100.00"),
        "late_deduct_per_occurrence": Decimal("20.00"),
        "early_deduct_per_occurrence": Decimal("20.00"),
        "missing_punch_deduct_per_occurrence": Decimal("10.00"),
    },
]


HOLIDAYS: list[dict[str, Any]] = [
    {
        "company_code": "C3",
        "date": date(2026, 9, 25),
        "name": "中秋节",
        "day_type": HolidayDayType.HOLIDAY,
    },
    {
        "company_code": "C3",
        "date": date(2026, 9, 27),
        "name": "调休上班",
        "day_type": HolidayDayType.ADJUSTED_WORKDAY,
    },
    *[
        {
            "company_code": "C3",
            "date": date(2026, 10, day),
            "name": "国庆节",
            "day_type": HolidayDayType.HOLIDAY,
        }
        for day in range(1, 8)
    ],
    {
        "company_code": "C3",
        "date": date(2026, 10, 10),
        "name": "调休上班",
        "day_type": HolidayDayType.ADJUSTED_WORKDAY,
    },
]


WEEKDAY_ADM: dict[int, list[str]] = {
    0: ["ADM"],
    1: ["ADM"],
    2: ["ADM"],
    3: ["ADM"],
    4: ["ADM"],
    5: [],
    6: [],
}
WEEKDAY_TEC: dict[int, list[str]] = {
    0: ["TEC"],
    1: ["TEC"],
    2: ["TEC"],
    3: ["TEC"],
    4: ["TEC"],
    5: [],
    6: [],
}
WEEKDAY_YL: dict[int, list[str]] = {
    0: ["YL"],
    1: ["YL"],
    2: ["YL"],
    3: ["YL"],
    4: ["YL"],
    5: [],
    6: [],
}

# Adjusted workdays and the employee plan's night-shift overrides per month.
ADJUSTED_WORKDAYS: dict[date, int] = {date(2026, 9, 1): 27, date(2026, 10, 1): 10}
NIGHT_OVERRIDE_DAYS: dict[date, int] = {
    date(2026, 8, 1): 27,
    date(2026, 9, 1): 30,
    date(2026, 10, 1): 29,
}


SURNAMES: tuple[str, ...] = tuple(
    "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
)
GIVEN_MALE: tuple[str, ...] = tuple(
    "伟强磊军勇杰涛明超刚华文辉志鹏斌宇浩凯健俊帆晨睿翔博毅航"
)
GIVEN_FEMALE: tuple[str, ...] = tuple(
    "芳娜静丽敏艳娟霞平丹梅红玲燕婷雪琳倩颖怡欣悦彤瑶佳慧蓉"
)

PUNCH_HEADER = [
    "工号",
    "姓名",
    "部门",
    "考勤日期",
    "打卡时间",
    "打卡结果",
    "打卡设备",
    "打卡地址",
    "考勤时间",
]
TRIP_HEADER = [
    "序号",
    "申请类型",
    "出差人部门",
    "出差人",
    "开始时间",
    "结束时间",
    "出差天数",
    "外出事由",
    "审批编号",
    "创建人",
    "审批结果",
    "审批状态",
]
OT_HEADER = [
    "序号",
    "部门",
    "加班开始时间",
    "加班结束时间",
    "加班时长（天/小时）",
    "加班原因",
    "审批编号",
    "创建人",
    "审批结果",
    "审批状态",
]
LEAVE_HEADER = [
    "序号",
    "部门",
    "请假类型",
    "请假天数",
    "休息开始时间",
    "休息结束时间",
    "请假说明",
    "审批编号",
    "创建人",
    "审批结果",
    "审批状态",
]

OA_ROWS_PER_MONTH: dict[ImportDataType, int] = {
    ImportDataType.TRIP: 10,
    ImportDataType.OT: 15,
    ImportDataType.LEAVE: 12,
}


# ---------------------------------------------------------------------------
# Deterministic generators
# ---------------------------------------------------------------------------


def _allocate_counts(company_code: str, scale: SeedScale) -> dict[str, int]:
    """Distribute one company's headcount over its active departments.

    Every active department gets at least one employee; the remainder follows
    the fixed weights with the largest-remainder method, so the total is exact.
    """
    active_codes = [
        data["dept_code"]
        for data in DEPARTMENTS
        if data["company_code"] == company_code and data.get("is_active", True)
    ]
    total = scale.employees[company_code]
    if total < len(active_codes):
        raise ValueError(
            f"Scale {scale.name} has {total} employees for {company_code}, "
            f"fewer than its {len(active_codes)} departments"
        )
    weights = DEPT_WEIGHTS[company_code]
    counts = dict.fromkeys(active_codes, 1)
    remaining = total - len(active_codes)
    weight_total = sum(weights[code] for code in active_codes)
    fractions: list[tuple[float, str]] = []
    assigned = 0
    for code in active_codes:
        raw = remaining * weights[code] / weight_total
        base = int(raw)
        counts[code] += base
        assigned += base
        fractions.append((-(raw - base), code))
    for _, code in sorted(fractions)[: remaining - assigned]:
        counts[code] += 1
    return counts


def _unique_name(rng: random.Random, used: set[str]) -> tuple[str, Gender]:
    for _ in range(2000):
        surname = rng.choice(SURNAMES)
        female = rng.random() < 0.5
        pool = GIVEN_FEMALE if female else GIVEN_MALE
        length = rng.choice((1, 2, 2))
        given = "".join(rng.choice(pool) for _ in range(length))
        name = surname + given
        if name in used:
            continue
        used.add(name)
        return name, Gender.FEMALE if female else Gender.MALE
    raise RuntimeError("Exhausted the generated-name pool")


def _random_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _pick_position(
    company_code: str, dept_code: str, slot: int, rng: random.Random
) -> str:
    candidates = DEPT_POSITIONS[company_code][dept_code]
    if len(candidates) == 1:
        return candidates[0]
    if slot == 0:
        return candidates[0]
    if "P2" in candidates and slot % 6 == 0:
        return "P2"
    return rng.choice(candidates)


def generate_employees(scale: SeedScale) -> list[dict[str, Any]]:
    """Build the deterministic employee rows for one seed scale.

    C4 is a fixed payroll demo dataset (``C4_EMPLOYEES``) and never generated;
    the scale still records its 15 employees so both scales agree on the
    company's size.
    """
    rows: list[dict[str, Any]] = []
    generated_codes = set(scale.employees) - {PAYROLL_COMPANY_CODE}
    for company_index, company in enumerate(COMPANIES):
        if company["company_code"] not in generated_codes:
            continue
        rows.extend(
            _generate_company_employees(company["company_code"], company_index, scale)
        )
    return rows


def _generate_company_employees(
    company_code: str, company_index: int, scale: SeedScale
) -> list[dict[str, Any]]:
    rng = random.Random(SEED_RANDOM_SEED + company_index * 7919)
    counts = _allocate_counts(company_code, scale)
    departments = [
        data
        for data in DEPARTMENTS
        if data["company_code"] == company_code and data.get("is_active", True)
    ]
    used_names: set[str] = set()
    prefix = {"C1": 1000, "C2": 2000, "C3": 3000}[company_code]
    next_number = prefix + 1
    rows: list[dict[str, Any]] = []
    leader_numbers: set[str] = set()

    def make(
        dept_code: str,
        position_code: str,
        manager_no: str | None,
        *,
        hire_date: date | None = None,
    ) -> dict[str, Any]:
        nonlocal next_number
        employee_no = f"E{next_number:04d}"
        next_number += 1
        name, gender = _unique_name(rng, used_names)
        return {
            "employee_no": employee_no,
            "name": name,
            "gender": gender,
            "company_code": company_code,
            "dept_code": dept_code,
            "position_code": position_code,
            "manager_no": manager_no,
            "status": EmployeeStatus.ACTIVE,
            "hire_date": hire_date
            or _random_date(rng, date(2012, 1, 1), date(2026, 10, 31)),
            "resign_date": None,
            "contract_type": ContractType.FULL_TIME,
            "daily_hours": Decimal("8.00"),
            "monthly_rest": 8,
            "confidentiality_level": rng.randint(1, 5),
        }

    head_dept = departments[0]["dept_code"]
    head = make(head_dept, DEPT_POSITIONS[company_code][head_dept][0], None)
    head["hire_date"] = _random_date(rng, date(2010, 1, 1), date(2016, 12, 31))
    head["confidentiality_level"] = 5
    rows.append(head)
    leader_numbers.add(head["employee_no"])

    for department in departments:
        dept_code = department["dept_code"]
        count = counts[dept_code]
        dept_manager_no: str | None = None
        if dept_code == head_dept:
            count -= 1
            dept_manager_no = head["employee_no"]
        else:
            # The first employee of every other department leads it.
            pass
        for slot in range(count):
            is_manager = dept_code != head_dept and slot == 0
            if is_manager:
                manager_no = head["employee_no"]
            elif dept_code == head_dept:
                manager_no = head["employee_no"]
            else:
                manager_no = dept_manager_no
            employee = make(
                dept_code,
                _pick_position(company_code, dept_code, slot, rng),
                manager_no,
            )
            if is_manager:
                employee["confidentiality_level"] = 4
                dept_manager_no = employee["employee_no"]
                leader_numbers.add(employee["employee_no"])
            rows.append(employee)

    non_leaders = [row for row in rows if row["employee_no"] not in leader_numbers]
    for index, row in enumerate(non_leaders):
        roll = rng.random()
        if index == len(non_leaders) - 1 or roll < 0.035:
            row["status"] = EmployeeStatus.RESIGNED
            row["hire_date"] = _random_date(rng, date(2012, 1, 1), date(2024, 12, 31))
            row["resign_date"] = _random_date(
                rng, row["hire_date"] + timedelta(days=180), date(2026, 10, 31)
            )
        elif index == len(non_leaders) - 2 or roll < 0.085:
            row["status"] = EmployeeStatus.PROBATION
            row["hire_date"] = _random_date(rng, date(2026, 5, 1), date(2026, 10, 31))
        contract_roll = rng.random()
        if contract_roll < 0.79:
            row["contract_type"] = ContractType.FULL_TIME
            row["daily_hours"] = Decimal("8.00")
            row["monthly_rest"] = 8
        elif contract_roll < 0.87:
            row["contract_type"] = ContractType.PART_TIME
            row["daily_hours"] = Decimal(str(rng.choice((4, 5, 6))))
            row["monthly_rest"] = 4
        elif contract_roll < 0.93:
            row["contract_type"] = ContractType.INTERN
            row["daily_hours"] = Decimal(str(rng.choice((4, 5))))
            row["monthly_rest"] = 8
        else:
            row["contract_type"] = ContractType.LABOR
            row["daily_hours"] = Decimal("8.00")
            row["monthly_rest"] = 4

    # Guarantee contract variety even at small scales.
    contract_defaults = {
        ContractType.FULL_TIME: (Decimal("8.00"), 8),
        ContractType.PART_TIME: (Decimal("4.00"), 4),
        ContractType.INTERN: (Decimal("5.00"), 8),
        ContractType.LABOR: (Decimal("8.00"), 4),
    }
    for offset, contract_type in enumerate(ContractType):
        if any(row["contract_type"] == contract_type for row in non_leaders):
            continue
        target = non_leaders[-(offset + 3)]
        target["contract_type"] = contract_type
        target["daily_hours"], target["monthly_rest"] = contract_defaults[contract_type]

    # Cost centers: C3 has none (left «未分配»); C1/C2 map by department with
    # every 53rd employee intentionally unassigned for the «未分配» view.
    for index, row in enumerate(rows):
        if company_code == "C3" or index % 53 == 52:
            row["cost_org_code"] = None
        else:
            row["cost_org_code"] = DEPT_COST_CENTER[company_code][row["dept_code"]]
    if company_code != "C3" and not any(row["cost_org_code"] is None for row in rows):
        # Small scales may not reach the 53rd employee; keep the demo view.
        rows[-1]["cost_org_code"] = None

    if company_code == "C3":
        _apply_c3_employment_windows(non_leaders)
        if not any(row["position_code"] == "P2" for row in rows):
            # Small scales may not reach the sixth D1 slot; the position-scope
            # plan still needs at least one 园林工.
            candidates = [
                row
                for row in rows
                if row["dept_code"] == "D1" and row["employee_no"] not in leader_numbers
            ]
            if candidates:
                candidates[-1]["position_code"] = "P2"

    return rows


def _apply_c3_employment_windows(non_leaders: list[dict[str, Any]]) -> None:
    """Pin four C3 employees to interesting employment windows.

    The attendance demo needs a resignation before August, a resignation in
    September, a hire in September, and a hire in October so every expansion
    and calculation month exercises the employment-window bounds.
    """
    if len(non_leaders) < 6:
        raise ValueError("C3 needs at least six non-leading employees")
    pre_august, resigned_sept, hire_sept, hire_oct = non_leaders[-6:-2]
    pre_august.update(
        status=EmployeeStatus.RESIGNED,
        hire_date=date(2019, 1, 1),
        resign_date=date(2026, 6, 30),
    )
    resigned_sept.update(
        status=EmployeeStatus.RESIGNED,
        hire_date=date(2020, 4, 1),
        resign_date=date(2026, 9, 10),
    )
    hire_sept.update(
        status=EmployeeStatus.ACTIVE,
        hire_date=date(2026, 9, 15),
        resign_date=None,
    )
    hire_oct.update(
        status=EmployeeStatus.ACTIVE,
        hire_date=date(2026, 10, 8),
        resign_date=None,
    )


# ---------------------------------------------------------------------------
# Organization seeders
# ---------------------------------------------------------------------------


def _seed_companies(session: Session) -> dict[str, Company]:
    companies = {
        company.company_code: company for company in session.exec(select(Company)).all()
    }
    for data in COMPANIES:
        if data["company_code"] in companies:
            continue
        company = Company(**data)
        session.add(company)
        session.flush()
        companies[company.company_code] = company
    return companies


def _seed_departments(
    session: Session, companies: dict[str, Company]
) -> dict[tuple[Any, str], Department]:
    departments = {
        (department.company_id, department.dept_code): department
        for department in session.exec(select(Department)).all()
    }
    for data in DEPARTMENTS:
        company = companies[data["company_code"]]
        key = (company.id, data["dept_code"])
        if key in departments:
            continue

        parent_id = None
        parent_code = data["parent_code"]
        if parent_code is not None:
            parent = departments.get((company.id, parent_code))
            if parent is None:
                logger.warning(
                    "Skipping seed department %s: parent %s is missing",
                    data["dept_code"],
                    parent_code,
                )
                continue
            parent_id = parent.id

        department = Department(
            company_id=company.id,
            dept_code=data["dept_code"],
            dept_name=data["dept_name"],
            parent_id=parent_id,
            order_no=data["order_no"],
            is_active=data.get("is_active", True),
        )
        session.add(department)
        session.flush()
        departments[key] = department
    return departments


def _seed_positions(
    session: Session,
    companies: dict[str, Company],
    departments: dict[tuple[Any, str], Department],
) -> None:
    positions = {
        (position.company_id, position.position_code): position
        for position in session.exec(select(Position)).all()
    }
    for data in POSITIONS:
        company = companies[data["company_code"]]
        key = (company.id, data["position_code"])
        if key in positions:
            continue

        dept_id = None
        dept_code = data["dept_code"]
        if dept_code is not None:
            department = departments.get((company.id, dept_code))
            if department is None:
                logger.warning(
                    "Skipping seed position %s: default department %s is missing",
                    data["position_code"],
                    dept_code,
                )
                continue
            dept_id = department.id

        position = Position(
            company_id=company.id,
            position_code=data["position_code"],
            position_name=data["position_name"],
            dept_id=dept_id,
            order_no=data["order_no"],
            is_active=data.get("is_active", True),
        )
        session.add(position)
        session.flush()
        positions[key] = position


def _seed_cost_centers(session: Session, companies: dict[str, Company]) -> None:
    cost_centers = {
        (cost_center.company_id, cost_center.cost_org_code): cost_center
        for cost_center in session.exec(select(CostCenter)).all()
    }
    for data in COST_CENTERS:
        company = companies[data["company_code"]]
        key = (company.id, data["cost_org_code"])
        if key in cost_centers:
            continue

        parent_id = None
        parent_code = data["parent_code"]
        if parent_code is not None:
            parent = cost_centers.get((company.id, parent_code))
            if parent is None:
                logger.warning(
                    "Skipping seed cost center %s: parent %s is missing",
                    data["cost_org_code"],
                    parent_code,
                )
                continue
            parent_id = parent.id

        cost_center = CostCenter(
            company_id=company.id,
            cost_org_code=data["cost_org_code"],
            cost_org_name=data["cost_org_name"],
            parent_id=parent_id,
            budget=data["budget"],
            warn_pct=data["warn_pct"],
            order_no=data["order_no"],
            is_active=data.get("is_active", True),
        )
        session.add(cost_center)
        session.flush()
        cost_centers[key] = cost_center


def _seed_employees(
    session: Session, companies: dict[str, Company], scale: SeedScale
) -> None:
    employees = {
        employee.employee_no: employee
        for employee in session.exec(select(Employee)).all()
    }
    departments = {
        (department.company_id, department.dept_code): department
        for department in session.exec(select(Department)).all()
    }
    positions = {
        (position.company_id, position.position_code): position
        for position in session.exec(select(Position)).all()
    }
    cost_centers = {
        (cost_center.company_id, cost_center.cost_org_code): cost_center
        for cost_center in session.exec(select(CostCenter)).all()
    }

    payroll_employees = [
        {**data, "company_code": PAYROLL_COMPANY_CODE} for data in C4_EMPLOYEES
    ]
    for data in (*generate_employees(scale), *payroll_employees):
        if data["employee_no"] in employees:
            continue

        company = companies[data["company_code"]]
        department = departments.get((company.id, data["dept_code"]))
        position = positions.get((company.id, data["position_code"]))
        if department is None or position is None:
            logger.warning(
                "Skipping seed employee %s: department or position is missing",
                data["employee_no"],
            )
            continue

        cost_org_id = None
        cost_org_code = data.get("cost_org_code")
        if cost_org_code is not None:
            cost_center = cost_centers.get((company.id, cost_org_code))
            if cost_center is None:
                logger.warning(
                    "Skipping seed employee %s: cost center %s is missing",
                    data["employee_no"],
                    cost_org_code,
                )
                continue
            cost_org_id = cost_center.id

        manager_id = None
        manager_no = data.get("manager_no")
        if manager_no is not None:
            manager = employees.get(manager_no)
            if manager is None:
                logger.warning(
                    "Skipping seed employee %s: manager %s is missing",
                    data["employee_no"],
                    manager_no,
                )
                continue
            manager_id = manager.id

        employee = Employee(
            employee_no=data["employee_no"],
            name=data["name"],
            gender=data.get("gender"),
            dept_id=department.id,
            position_id=position.id,
            cost_org_id=cost_org_id,
            manager_id=manager_id,
            status=data["status"],
            hire_date=data["hire_date"],
            resign_date=data.get("resign_date"),
            contract_type=data.get("contract_type", ContractType.FULL_TIME),
            daily_hours=data.get("daily_hours"),
            monthly_rest=data.get("monthly_rest"),
            confidentiality_level=data.get("confidentiality_level"),
            note=data.get("note"),
        )
        session.add(employee)
        session.flush()
        employees[employee.employee_no] = employee


def _seed_users(session: Session) -> None:
    existing = {user.email for user in session.exec(select(User)).all()}
    hashed_password: str | None = None
    for email, full_name in USERS:
        if email in existing:
            continue
        if hashed_password is None:
            # All generated users share the same development password; hash it
            # once so re-seeding stays cheap.
            hashed_password = get_password_hash(USER_PASSWORD)
        session.add(
            User(
                email=email,
                full_name=full_name,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=False,
            )
        )
    session.flush()


def _seed_shifts(session: Session, companies: dict[str, Company]) -> None:
    shifts = {
        (shift.company_id, shift.shift_code): shift
        for shift in session.exec(select(Shift)).all()
    }
    for data in SHIFTS:
        company = companies[data["company_code"]]
        key = (company.id, data["shift_code"])
        if key in shifts:
            continue
        shift = Shift(
            company_id=company.id,
            **{name: value for name, value in data.items() if name != "company_code"},
        )
        session.add(shift)
        session.flush()
        shifts[key] = shift


def _seed_attendance_rules(session: Session, companies: dict[str, Company]) -> None:
    configured = {
        rule.company_id for rule in session.exec(select(AttendanceRule)).all()
    }
    for data in ATTENDANCE_RULES:
        company = companies[data["company_code"]]
        if company.id in configured:
            continue
        rule = AttendanceRule(
            company_id=company.id,
            **{name: value for name, value in data.items() if name != "company_code"},
        )
        session.add(rule)
        session.flush()
        configured.add(company.id)


def _seed_holidays(session: Session, companies: dict[str, Company]) -> None:
    holidays = {
        (holiday.company_id, holiday.date)
        for holiday in session.exec(select(Holiday)).all()
    }
    for data in HOLIDAYS:
        company = companies[data["company_code"]]
        key = (company.id, data["date"])
        if key in holidays:
            continue
        holiday = Holiday(
            company_id=company.id,
            **{name: value for name, value in data.items() if name != "company_code"},
        )
        session.add(holiday)
        session.flush()
        holidays.add(key)


# ---------------------------------------------------------------------------
# Attendance seeders
# ---------------------------------------------------------------------------


def _plan_days(
    plan: dict[str, Any],
    shifts: dict[str, Shift],
) -> list[dict[str, Any]]:
    """Expand a weekday pattern and date overrides into per-day rows."""
    month: date = plan["month"]
    last_day = calendar.monthrange(month.year, month.month)[1]
    rows: list[dict[str, Any]] = []
    for day_of_month in range(1, last_day + 1):
        codes = plan["day_overrides"].get(day_of_month)
        if codes is None:
            weekday = date(month.year, month.month, day_of_month).weekday()
            codes = plan["weekdays"].get(weekday, [])
        for seq, code in enumerate(codes):
            rows.append(
                {
                    "day_of_month": day_of_month,
                    "seq": seq,
                    "shift_id": shifts[code].id,
                }
            )
    return rows


def _plan_specs(month: date, target_employee_no: str) -> list[dict[str, Any]]:
    adjusted_day = ADJUSTED_WORKDAYS.get(month)
    night_day = NIGHT_OVERRIDE_DAYS[month]
    adjusted_overrides = {adjusted_day: ["ADM"]} if adjusted_day is not None else {}
    adjusted_tec = {adjusted_day: ["TEC"]} if adjusted_day is not None else {}
    adjusted_yl = {adjusted_day: ["YL"]} if adjusted_day is not None else {}
    employee_overrides: dict[int, list[str]] = {night_day: ["NIGHT"]}
    if adjusted_day is not None:
        employee_overrides[adjusted_day] = ["ADM"]
    return [
        {
            "month": month,
            "plan_name": "行政班",
            "scope_type": ScheduleScopeType.ALL,
            "scope_dept_codes": [],
            "scope_position_codes": [],
            "scope_employee_nos": [],
            "weekdays": WEEKDAY_ADM,
            "day_overrides": adjusted_overrides,
            "rule_overrides": None,
            "note": "全公司兜底方案"
            if adjusted_day is None
            else "全公司兜底方案；含调休上班",
        },
        {
            "month": month,
            "plan_name": "财务技术班",
            "scope_type": ScheduleScopeType.DEPT,
            "scope_dept_codes": ["D2"],
            "scope_position_codes": [],
            "scope_employee_nos": [],
            "weekdays": WEEKDAY_TEC,
            "day_overrides": adjusted_tec,
            "rule_overrides": None,
            "note": "财务部固定技术员班",
        },
        {
            "month": month,
            "plan_name": "园林班",
            "scope_type": ScheduleScopeType.POSITION,
            "scope_dept_codes": [],
            "scope_position_codes": ["P2"],
            "scope_employee_nos": [],
            "weekdays": WEEKDAY_YL,
            "day_overrides": adjusted_yl,
            "rule_overrides": {"ot_threshold_min": 15},
            "note": "园林工岗位方案；加班起算门槛覆盖为 15 分钟",
        },
        {
            "month": month,
            "plan_name": f"{target_employee_no}夜班",
            "scope_type": ScheduleScopeType.EMPLOYEE,
            "scope_dept_codes": [],
            "scope_position_codes": [],
            "scope_employee_nos": [target_employee_no],
            "weekdays": WEEKDAY_ADM,
            "day_overrides": employee_overrides,
            "rule_overrides": None,
            "note": "员工级方案：工作日行政班，含一次夜班",
        },
    ]


def _plan_target_employee(session: Session, company: Company) -> Employee:
    """The employee-scope plan target: an active production-line employee."""
    statement = (
        select(Employee)
        .join(Department, col(Employee.dept_id) == col(Department.id))
        .where(
            Department.company_id == company.id,
            Department.dept_code == "D5",
            Employee.status == EmployeeStatus.ACTIVE,
            col(Employee.hire_date) <= date(2026, 8, 1),
            col(Employee.resign_date).is_(None),
        )
        .order_by(col(Employee.employee_no))
        .limit(1)
    )
    employee = session.exec(statement).first()
    if employee is None:
        raise SystemExit(
            "Refusing to seed attendance plans: no active C3 production employee"
        )
    return employee


def _seed_attendance_plans(
    session: Session,
    companies: dict[str, Company],
    departments: dict[tuple[Any, str], Department],
) -> None:
    """Insert missing plans for each month and expand a month once.

    Expansion goes through the real service path so the demo roster matches
    what the API would produce. A month is expanded when at least one of its
    plans was just created or when it has no roster yet; healthy re-runs are
    no-ops, and a recreated plan is re-expanded.
    """
    company = companies["C3"]
    target = _plan_target_employee(session, company)
    shifts = {
        shift.shift_code: shift
        for shift in session.exec(
            select(Shift).where(col(Shift.company_id) == company.id)
        ).all()
    }
    positions = {
        position.position_code: position
        for position in session.exec(
            select(Position).where(col(Position.company_id) == company.id)
        ).all()
    }

    for month in ATTENDANCE_MONTHS:
        existing_names = {
            plan.plan_name
            for plan in session.exec(
                select(SchedulePlan).where(
                    col(SchedulePlan.company_id) == company.id,
                    col(SchedulePlan.month) == month,
                )
            ).all()
        }
        specs = _plan_specs(month, target.employee_no)
        missing = [spec for spec in specs if spec["plan_name"] not in existing_names]
        for data in missing:
            plan = SchedulePlan(
                company_id=company.id,
                month=month,
                plan_name=data["plan_name"],
                scope_type=data["scope_type"],
                note=data["note"],
            )
            session.add(plan)
            session.flush()
            for dept_code in data["scope_dept_codes"]:
                session.add(
                    PlanScope(
                        plan_id=plan.id,
                        scope_id=departments[(company.id, dept_code)].id,
                    )
                )
            for position_code in data["scope_position_codes"]:
                session.add(
                    PlanScope(
                        plan_id=plan.id,
                        scope_id=positions[position_code].id,
                    )
                )
            for employee_no in data["scope_employee_nos"]:
                employee = session.exec(
                    select(Employee).where(Employee.employee_no == employee_no)
                ).one()
                session.add(PlanScope(plan_id=plan.id, scope_id=employee.id))
            for day_row in _plan_days(data, shifts):
                session.add(PlanDay(plan_id=plan.id, **day_row))
            if data["rule_overrides"] is not None:
                session.add(PlanRuleOverride(plan_id=plan.id, **data["rule_overrides"]))
        session.flush()

        month_row = session.exec(
            select(AttendanceMonth).where(
                col(AttendanceMonth.company_id) == company.id,
                col(AttendanceMonth.month) == month,
            )
        ).first()
        if month_row is None:
            session.add(AttendanceMonth(company_id=company.id, month=month))
            session.flush()

        month_end = date(
            month.year, month.month, calendar.monthrange(month.year, month.month)[1]
        )
        has_entries = (
            session.exec(
                select(RosterEntry).where(
                    col(RosterEntry.company_id) == company.id,
                    col(RosterEntry.work_date) >= month,
                    col(RosterEntry.work_date) <= month_end,
                )
            ).first()
            is not None
        )
        if missing or not has_entries:
            change = expansion.expand_month(session, company.id, month)
            logger.info(
                "Expanded C3 roster for %s: added=%d updated=%d deleted=%d",
                month.strftime("%Y-%m"),
                change.added,
                change.updated,
                change.deleted,
            )


def _seed_attendance_manual_entries(
    session: Session, companies: dict[str, Company]
) -> None:
    """Insert the two documented September manual exceptions if missing."""
    company = companies["C3"]
    month = date(2026, 9, 1)
    employees = session.exec(
        select(Employee)
        .join(Department, col(Employee.dept_id) == col(Department.id))
        .where(
            Department.company_id == company.id,
            Employee.status == EmployeeStatus.ACTIVE,
            col(Employee.hire_date) <= date(2026, 8, 1),
            col(Employee.resign_date).is_(None),
        )
        .order_by(col(Employee.employee_no))
        .limit(2)
    ).all()
    if len(employees) < 2:
        return
    shifts = {
        shift.shift_code: shift
        for shift in session.exec(
            select(Shift).where(col(Shift.company_id) == company.id)
        ).all()
    }
    candidates = expansion.load_candidates(session, company.id, month)
    seeds: list[tuple[Employee, date, RosterState, list[str], str | None]] = [
        (employees[0], date(2026, 9, 10), RosterState.REST, [], "个人调休"),
        (
            employees[1],
            date(2026, 9, 11),
            RosterState.WORK,
            ["EARLY", "MID"],
            "临时双班",
        ),
    ]
    for employee, work_date, state, shift_codes, note in seeds:
        existing = session.exec(
            select(RosterEntry).where(
                col(RosterEntry.employee_id) == employee.id,
                col(RosterEntry.work_date) == work_date,
            )
        ).first()
        if existing is not None and existing.source == RosterSource.MANUAL:
            # A user-edited exception always wins over the documented seed.
            continue
        winner = expansion.resolve_winner(candidates, employee)
        if existing is None:
            entry = RosterEntry(
                company_id=company.id,
                employee_id=employee.id,
                work_date=work_date,
                state=state,
                source=RosterSource.MANUAL,
                plan_id=winner.plan_id if winner is not None else None,
                note=note,
            )
            session.add(entry)
        else:
            entry = existing
            entry.state = state
            entry.source = RosterSource.MANUAL
            entry.plan_id = winner.plan_id if winner is not None else None
            entry.note = note
            session.add(entry)
            for row in session.exec(
                select(RosterEntryShift).where(
                    col(RosterEntryShift.roster_entry_id) == entry.id
                )
            ).all():
                session.delete(row)
        session.flush()
        for seq, shift_code in enumerate(shift_codes):
            shift = shifts[shift_code]
            session.add(
                RosterEntryShift(
                    roster_entry_id=entry.id,
                    seq=seq,
                    shift_id=shift.id,
                    shift_code=shift.shift_code,
                    shift_name=shift.shift_name,
                    start_time=shift.start_time,
                    end_time=shift.end_time,
                    cross_day=shift.cross_day,
                    break_start=shift.break_start,
                    break_end=shift.break_end,
                    rest_minutes=shift.rest_minutes,
                )
            )
    session.flush()


# ---------------------------------------------------------------------------
# Import CSV generation
# ---------------------------------------------------------------------------


def _month_end(month: date) -> date:
    return date(
        month.year, month.month, calendar.monthrange(month.year, month.month)[1]
    )


def _csv_bytes(header: list[str], rows: list[list[str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def _punch_rows(session: Session, company: Company, month: date) -> list[list[str]]:
    """Derive punch rows from the expanded September-style roster."""
    start, end = month, _month_end(month)
    entries = session.exec(
        select(RosterEntry).where(
            col(RosterEntry.company_id) == company.id,
            col(RosterEntry.work_date) >= start,
            col(RosterEntry.work_date) <= end,
        )
    ).all()
    if not entries:
        return []
    entry_ids = [entry.id for entry in entries]
    shift_rows = session.exec(
        select(RosterEntryShift)
        .where(col(RosterEntryShift.roster_entry_id).in_(entry_ids))
        .order_by(col(RosterEntryShift.roster_entry_id), col(RosterEntryShift.seq))
    ).all()
    shifts_by_entry: dict[Any, list[RosterEntryShift]] = {}
    for row in shift_rows:
        shifts_by_entry.setdefault(row.roster_entry_id, []).append(row)

    employees = {
        employee.id: employee
        for employee in session.exec(
            select(Employee).where(
                col(Employee.id).in_([entry.employee_id for entry in entries])
            )
        ).all()
    }
    departments = {
        department.id: department
        for department in session.exec(select(Department)).all()
    }
    rng = random.Random(SEED_RANDOM_SEED + month.month * 31 + 1)
    seen: set[tuple[str, date, datetime]] = set()
    rows: list[list[str]] = []

    def add_punch(
        employee: Employee,
        department: Department,
        work_date: date,
        punch_at: datetime,
        result: str,
    ) -> None:
        key = (employee.employee_no, work_date, punch_at)
        if key in seen:
            return
        seen.add(key)
        rows.append(
            [
                employee.employee_no,
                employee.name,
                department.dept_name,
                work_date.isoformat(),
                punch_at.strftime("%Y-%m-%d %H:%M"),
                result,
                "考勤机",
                "一号门",
                punch_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    for entry in entries:
        if entry.state != RosterState.WORK:
            continue
        employee = employees.get(entry.employee_id)
        if employee is None:
            continue
        department = departments[employee.dept_id]
        for shift in shifts_by_entry.get(entry.id, []):
            start_at = datetime.combine(entry.work_date, shift.start_time)
            end_date = entry.work_date + (
                timedelta(days=1) if shift.cross_day else timedelta()
            )
            end_at = datetime.combine(end_date, shift.end_time)
            if rng.random() < 0.04:
                start_at += timedelta(minutes=rng.randint(6, 30))
                in_result = "迟到"
            else:
                start_at -= timedelta(minutes=rng.randint(0, 10))
                in_result = "正常"
            if rng.random() < 0.03:
                end_at -= timedelta(minutes=rng.randint(6, 25))
                out_result = "早退"
            else:
                end_at += timedelta(minutes=rng.randint(0, 20))
                out_result = "正常"
            if rng.random() >= 0.008:
                add_punch(employee, department, entry.work_date, start_at, in_result)
            if rng.random() >= 0.015:
                add_punch(employee, department, entry.work_date, end_at, out_result)

    rows.sort(key=lambda row: (row[0], row[3], row[4]))
    return rows


def _oa_employees(
    session: Session, company: Company
) -> list[tuple[Employee, Department]]:
    """Employees employed across the whole demo window, ordered by number."""
    rows = session.exec(
        select(Employee, Department)
        .join(Department, col(Employee.dept_id) == col(Department.id))
        .where(
            Department.company_id == company.id,
            col(Employee.status).in_([EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION]),
            col(Employee.hire_date) <= date(2026, 8, 1),
            col(Employee.resign_date).is_(None),
        )
        .order_by(col(Employee.employee_no))
    ).all()
    return [(employee, department) for employee, department in rows]


def _pick_oa_employees(
    pool: list[tuple[Employee, Department]], offset: int, count: int
) -> list[tuple[Employee, Department]]:
    if not pool:
        return []
    return [pool[(offset + index) % len(pool)] for index in range(count)]


def _oa_rows(
    session: Session, company: Company, month: date, data_type: ImportDataType
) -> list[list[str]]:
    pool = _oa_employees(session, company)
    count = OA_ROWS_PER_MONTH[data_type]
    if data_type == ImportDataType.TRIP:
        rows: list[list[str]] = []
        for index, (employee, department) in enumerate(
            _pick_oa_employees(pool, 10 + month.month, count)
        ):
            day = 3 + index
            if date(month.year, month.month, day).weekday() >= 5:
                day += 2
            day = min(day, calendar.monthrange(month.year, month.month)[1])
            start_at = datetime.combine(date(month.year, month.month, day), time(8, 0))
            end_at = datetime.combine(date(month.year, month.month, day), time(18, 0))
            rows.append(
                [
                    str(index + 1),
                    "出差",
                    department.dept_name,
                    employee.name,
                    start_at.strftime("%Y-%m-%d %H:%M:%S"),
                    end_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "1",
                    "客户现场支持",
                    f"AP-T-{month:%Y%m}-{index + 1:03d}",
                    employee.name,
                    "审批通过",
                    "已结束",
                ]
            )
        return rows

    if data_type == ImportDataType.OT:
        rows = []
        for index, (employee, department) in enumerate(
            _pick_oa_employees(pool, 40 + month.month, count)
        ):
            day = 4 + index
            if date(month.year, month.month, day).weekday() >= 5:
                day += 2
            day = min(day, calendar.monthrange(month.year, month.month)[1])
            start_at = datetime.combine(
                date(month.year, month.month, day), time(18, 30)
            )
            end_at = datetime.combine(date(month.year, month.month, day), time(20, 30))
            rows.append(
                [
                    str(index + 1),
                    department.dept_name,
                    start_at.strftime("%Y-%m-%d %H:%M:%S"),
                    end_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "2",
                    "赶工",
                    f"AP-OT-{month:%Y%m}-{index + 1:03d}",
                    employee.name,
                    "审批通过",
                    "已结束",
                ]
            )
        return rows

    rows = []
    leave_types = ["事假", "带薪假（需出示相关证明）", "调休"]
    for index, (employee, department) in enumerate(
        _pick_oa_employees(pool, 70 + month.month, count)
    ):
        day = 5 + index
        if date(month.year, month.month, day).weekday() >= 5:
            day += 2
        day = min(day, calendar.monthrange(month.year, month.month)[1])
        leave_type = leave_types[index % len(leave_types)]
        if leave_type == "事假" and index % 2 == 1:
            start_at = datetime.combine(date(month.year, month.month, day), time(8, 30))
            end_at = datetime.combine(date(month.year, month.month, day), time(12, 0))
            days = "0.5"
        else:
            start_at = datetime.combine(date(month.year, month.month, day), time(8, 30))
            end_at = datetime.combine(date(month.year, month.month, day), time(17, 30))
            days = "1"
        rows.append(
            [
                str(index + 1),
                department.dept_name,
                leave_type,
                days,
                start_at.strftime("%Y-%m-%d %H:%M:%S"),
                end_at.strftime("%Y-%m-%d %H:%M:%S"),
                "个人事务",
                f"AP-LV-{month:%Y%m}-{index + 1:03d}",
                employee.name,
                "审批通过",
                "已结束",
            ]
        )
    return rows


def _build_import_file(
    session: Session, company: Company, month: date, data_type: ImportDataType
) -> tuple[bytes, str]:
    if data_type == ImportDataType.PUNCH:
        return (
            _csv_bytes(PUNCH_HEADER, _punch_rows(session, company, month)),
            f"punch-{month:%Y-%m}.csv",
        )
    if data_type == ImportDataType.TRIP:
        return (
            _csv_bytes(TRIP_HEADER, _oa_rows(session, company, month, data_type)),
            f"oa-trip-{month:%Y-%m}.csv",
        )
    if data_type == ImportDataType.OT:
        return (
            _csv_bytes(OT_HEADER, _oa_rows(session, company, month, data_type)),
            f"oa-overtime-{month:%Y-%m}.csv",
        )
    return (
        _csv_bytes(LEAVE_HEADER, _oa_rows(session, company, month, data_type)),
        f"oa-leave-{month:%Y-%m}.csv",
    )


def _seed_import_batches(session: Session, companies: dict[str, Company]) -> None:
    """Commit generated punch and OA files through the real import path.

    A scope that already has a committed batch is skipped, so re-running the
    seed never supersedes or rewrites a user's import.
    """
    company = companies["C3"]
    operator = session.exec(
        select(User).where(col(User.email) == settings.FIRST_SUPERUSER)
    ).first()
    if operator is None:
        raise SystemExit(
            "Refusing to seed import batches: the first superuser is "
            "missing. Run backend/scripts/prestart.sh or "
            "app/initial_data.py first."
        )
    for month in ATTENDANCE_MONTHS:
        for data_type in (
            ImportDataType.PUNCH,
            ImportDataType.TRIP,
            ImportDataType.OT,
            ImportDataType.LEAVE,
        ):
            committed = session.exec(
                select(ImportBatch).where(
                    col(ImportBatch.company_id) == company.id,
                    col(ImportBatch.data_type) == data_type,
                    col(ImportBatch.month) == month,
                    col(ImportBatch.status) == ImportBatchStatus.COMMITTED,
                )
            ).first()
            if committed is not None:
                continue
            template = session.exec(
                select(ImportMappingTemplate).where(
                    col(ImportMappingTemplate.company_id) == company.id,
                    col(ImportMappingTemplate.data_type) == data_type,
                )
            ).first()
            content, file_name = _build_import_file(session, company, month, data_type)
            preview = imports.preview_import(
                session,
                company_id=company.id,
                data_type=data_type,
                month=month,
                operator=operator,
                content=content,
                file_name=file_name,
            )
            if preview.stats.error_records:
                messages = "; ".join(
                    f"{error.code}:{error.message}" for error in preview.errors[:3]
                )
                raise RuntimeError(
                    f"Generated {data_type.value} import for "
                    f"{month:%Y-%m} has {preview.stats.error_records} row errors: "
                    f"{messages}"
                )
            imports.commit_batch(
                session,
                preview.batch.id,
                operator=operator,
                # A template the user already maintains wins over the generated
                # mapping; the batch still records its own mapping snapshot.
                save_mapping_template=template is None,
            )
            logger.info(
                "Imported %s for %s: source=%d valid=%d skipped=%d warnings=%d",
                data_type.value,
                month.strftime("%Y-%m"),
                preview.stats.source_rows,
                preview.stats.valid_records,
                preview.stats.skipped_records,
                preview.stats.warning_records,
            )


def _seed_calculations(session: Session, companies: dict[str, Company]) -> None:
    """Calculate every demo month once, leaving it in the calculated state."""
    company = companies["C3"]
    for month in ATTENDANCE_MONTHS:
        month_row = session.exec(
            select(AttendanceMonth).where(
                col(AttendanceMonth.company_id) == company.id,
                col(AttendanceMonth.month) == month,
            )
        ).first()
        if month_row is None:
            continue
        if month_row.status in (
            AttendanceMonthStatus.CONFIRMED,
            AttendanceMonthStatus.LOCKED,
        ):
            continue
        success = session.exec(
            select(CalcRun).where(
                col(CalcRun.attendance_month_id) == month_row.id,
                col(CalcRun.status) == CalcRunStatus.SUCCESS,
            )
        ).first()
        if success is not None:
            continue
        calc_run = month_service.calculate_month(
            session, company_id=company.id, month=month
        )
        summary = calc_run.summary or {}
        logger.info(
            "Calculated C3 for %s: employees=%s days=%s",
            month.strftime("%Y-%m"),
            summary.get("employees_calculated"),
            summary.get("days_total"),
        )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def seed(session: Session, *, scale: SeedScale = FULL_SCALE) -> None:
    companies = _seed_companies(session)
    departments = _seed_departments(session, companies)
    _seed_positions(session, companies, departments)
    _seed_cost_centers(session, companies)
    _seed_employees(session, companies, scale)
    _seed_users(session)
    _seed_shifts(session, companies)
    _seed_attendance_rules(session, companies)
    _seed_holidays(session, companies)
    session.commit()

    _seed_attendance_plans(session, companies, departments)
    _seed_attendance_manual_entries(session, companies)
    session.commit()

    _seed_import_batches(session, companies)
    _seed_calculations(session, companies)
    session.commit()


def main() -> None:
    if settings.FASTAPI_ENV != "development":
        raise SystemExit("Refusing to seed: FASTAPI_ENV must be 'development'.")
    with Session(engine) as session:
        seed(session)
    logger.info(
        "Development seed data is up to date (scale=%s, %s)",
        FULL_SCALE.name,
        ", ".join(
            f"{code}={count}" for code, count in sorted(FULL_SCALE.employees.items())
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
