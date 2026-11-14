"""Development-only seed data.

Run manually from the backend directory with ``uv run python -m app.seed_dev``.
The script refuses to run unless ``FASTAPI_ENV=development`` and only inserts
rows that are missing by business code, so user edits are never overwritten.
"""

import calendar
import logging
from datetime import date, time
from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.db import engine
from app.enums import (
    ContractType,
    EmployeeStatus,
    Gender,
    HolidayDayType,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import (
    AttendanceMonth,
    AttendanceRule,
    Company,
    CostCenter,
    Department,
    Employee,
    Holiday,
    PlanDay,
    PlanRuleOverride,
    PlanScope,
    Position,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
)
from app.services.attendance import expansion

logger = logging.getLogger(__name__)

COMPANIES: list[dict[str, Any]] = [
    {"company_code": "C1", "company_name": "荣新建设", "note": "完整组织示例"},
    {"company_code": "C2", "company_name": "荣新科技", "note": "小型组织示例"},
    {"company_code": "C3", "company_name": "荣新物流", "note": "空公司示例"},
    {
        "company_code": "C4",
        "company_name": "荣新考勤演示",
        "note": "考勤演示公司；C1-C3 不包含考勤数据",
    },
]

# Parents are listed before their children so one pass can resolve every
# ``parent_code`` to the row inserted earlier in the same run.
DEPARTMENTS: list[dict[str, Any]] = [
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
    {
        # Inactive department without active employee references, used to
        # demonstrate the inactive state; keep seeded employees elsewhere.
        "company_code": "C1",
        "dept_code": "D7",
        "dept_name": "旧项目部",
        "parent_code": "D1",
        "order_no": 9,
        "is_active": False,
    },
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
    # Attendance demo company. Attendance seed rows never touch C1-C3.
    {
        "company_code": "C4",
        "dept_code": "D1",
        "dept_name": "生产部",
        "parent_code": None,
        "order_no": 0,
    },
    {
        "company_code": "C4",
        "dept_code": "D2",
        "dept_name": "财务部",
        "parent_code": None,
        "order_no": 1,
    },
    {
        "company_code": "C4",
        "dept_code": "D3",
        "dept_name": "技术部",
        "parent_code": None,
        "order_no": 2,
    },
    {
        "company_code": "C4",
        "dept_code": "D4",
        "dept_name": "行政部",
        "parent_code": None,
        "order_no": 3,
    },
]


# Positions are company-level and reference their default department by code.
# ``dept_code`` is resolved within the position's company.
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
        "order_no": 1,
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
    {
        # No default department: the employee form must not prefill one.
        "company_code": "C1",
        "position_code": "P6",
        "position_name": "行政专员",
        "dept_code": None,
        "order_no": 2,
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
        "company_code": "C4",
        "position_code": "P1",
        "position_name": "生产操作工",
        "dept_code": "D1",
        "order_no": 0,
    },
    {
        "company_code": "C4",
        "position_code": "P2",
        "position_name": "园林工",
        "dept_code": "D1",
        "order_no": 1,
    },
    {
        "company_code": "C4",
        "position_code": "P3",
        "position_name": "会计",
        "dept_code": "D2",
        "order_no": 0,
    },
    {
        "company_code": "C4",
        "position_code": "P4",
        "position_name": "技术员",
        "dept_code": "D3",
        "order_no": 0,
    },
    {
        "company_code": "C4",
        "position_code": "P5",
        "position_name": "行政专员",
        "dept_code": "D4",
        "order_no": 0,
    },
]


# Multi-level cost center tree for the full company, a two-level tree for the
# small company, and an inactive node without employee references. Parents are
# listed before their children so one pass can resolve every ``parent_code``.
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
    {
        # Inactive cost center without active employee references, used to
        # demonstrate the inactive state; keep seeded employees elsewhere.
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
]


# Managers are listed before their reports so one pass can resolve
# ``manager_no``. Numbers are globally unique and drive the default sort order.
# Dates are fixed and never in the future. Employees have no login accounts.
EMPLOYEES: list[dict[str, Any]] = [
    {
        "employee_no": "E1001",
        "name": "张建国",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D1",
        "position_code": "P1",
        "cost_org_code": "K1",
        "manager_no": None,
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2015, 3, 1),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 5,
    },
    {
        "employee_no": "E1002",
        "name": "王丽",
        "gender": Gender.FEMALE,
        "company_code": "C1",
        "dept_code": "D5",
        "position_code": "P5",
        "cost_org_code": "K5",
        "manager_no": "E1001",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2017, 6, 12),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 4,
    },
    {
        "employee_no": "E1003",
        "name": "李强",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D2",
        "position_code": "P2",
        "cost_org_code": "K2",
        "manager_no": "E1001",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2016, 9, 1),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 4,
        "confidentiality_level": 4,
    },
    {
        "employee_no": "E1004",
        "name": "黄国锋",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D3",
        "position_code": "P3",
        "cost_org_code": "K3",
        "manager_no": "E1003",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2018, 4, 15),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 4,
        "confidentiality_level": 3,
    },
    {
        "employee_no": "E1005",
        "name": "赵敏",
        "gender": Gender.FEMALE,
        "company_code": "C1",
        "dept_code": "D6",
        "position_code": "P4",
        "cost_org_code": "K5",
        "manager_no": "E1001",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2019, 2, 20),
        "contract_type": ContractType.PART_TIME,
        "daily_hours": Decimal("4.00"),
        "monthly_rest": 8,
        "confidentiality_level": 4,
    },
    {
        "employee_no": "E1006",
        "name": "陈静",
        "gender": Gender.FEMALE,
        "company_code": "C1",
        "dept_code": "D5",
        "position_code": "P5",
        "cost_org_code": "K1",
        "manager_no": "E1001",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2020, 7, 1),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 3,
    },
    {
        "employee_no": "E1007",
        "name": "刘洋",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D3",
        "position_code": "P3",
        "cost_org_code": "K3",
        "manager_no": "E1004",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2021, 3, 10),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 4,
        "confidentiality_level": 2,
    },
    {
        "employee_no": "E1008",
        "name": "周杰",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D3",
        "position_code": "P3",
        "cost_org_code": "K3",
        "manager_no": "E1004",
        "status": EmployeeStatus.PROBATION,
        "hire_date": date(2026, 9, 1),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 4,
        "confidentiality_level": 1,
    },
    {
        "employee_no": "E1009",
        "name": "吴刚",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D3",
        "position_code": "P3",
        "cost_org_code": None,
        "manager_no": "E1004",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2022, 5, 18),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 4,
        "confidentiality_level": 2,
        "note": "成本归属未分配，用于演示「未分配」视图",
    },
    {
        "employee_no": "E1010",
        "name": "郑爽",
        "gender": Gender.FEMALE,
        "company_code": "C1",
        "dept_code": "D5",
        "position_code": "P5",
        "cost_org_code": "K5",
        "manager_no": "E1002",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2023, 8, 1),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 2,
    },
    {
        "employee_no": "E1011",
        "name": "冯涛",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D2",
        "position_code": "P3",
        "cost_org_code": "K2",
        "manager_no": "E1003",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2020, 12, 1),
        "contract_type": ContractType.LABOR,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 4,
        "confidentiality_level": 1,
    },
    {
        "employee_no": "E1012",
        "name": "孙丽",
        "gender": Gender.FEMALE,
        "company_code": "C1",
        "dept_code": "D6",
        "position_code": "P4",
        "cost_org_code": "K1",
        "manager_no": "E1001",
        "status": EmployeeStatus.PROBATION,
        "hire_date": date(2026, 10, 1),
        "contract_type": ContractType.INTERN,
        "daily_hours": Decimal("6.00"),
        "monthly_rest": 8,
        "confidentiality_level": 1,
    },
    {
        "employee_no": "E1013",
        "name": "李娜",
        "gender": Gender.FEMALE,
        "company_code": "C1",
        "dept_code": "D6",
        "position_code": "P4",
        "cost_org_code": None,
        "manager_no": "E1001",
        "status": EmployeeStatus.RESIGNED,
        "hire_date": date(2017, 5, 2),
        "resign_date": date(2025, 12, 31),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 4,
        "note": "已离职，成本归属未分配",
    },
    {
        "employee_no": "E1014",
        "name": "王强",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D2",
        "position_code": "P2",
        "cost_org_code": "K2",
        "manager_no": "E1003",
        "status": EmployeeStatus.RESIGNED,
        "hire_date": date(2016, 11, 1),
        "resign_date": date(2024, 6, 30),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 4,
        "confidentiality_level": 3,
    },
    {
        "employee_no": "E1015",
        "name": "张伟",
        "gender": Gender.MALE,
        "company_code": "C1",
        "dept_code": "D4",
        "position_code": "P3",
        "cost_org_code": "K4",
        "manager_no": "E1003",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2019, 7, 8),
        "contract_type": ContractType.PART_TIME,
        "daily_hours": Decimal("5.00"),
        "monthly_rest": 8,
        "confidentiality_level": 2,
    },
    {
        "employee_no": "E1016",
        "name": "周敏",
        "gender": Gender.FEMALE,
        "company_code": "C1",
        "dept_code": "D1",
        "position_code": "P6",
        "cost_org_code": "K1",
        "manager_no": "E1001",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2024, 2, 19),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 2,
    },
    {
        "employee_no": "E2001",
        "name": "李雷",
        "gender": Gender.MALE,
        "company_code": "C2",
        "dept_code": "K1",
        "position_code": "K1",
        "cost_org_code": "K1",
        "manager_no": None,
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2018, 3, 1),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 5,
    },
    {
        "employee_no": "E2002",
        "name": "韩梅梅",
        "gender": Gender.FEMALE,
        "company_code": "C2",
        "dept_code": "K2",
        "position_code": "K1",
        "cost_org_code": "K2",
        "manager_no": "E2001",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2019, 6, 1),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 4,
    },
    {
        "employee_no": "E2003",
        "name": "王芳",
        "gender": Gender.FEMALE,
        "company_code": "C2",
        "dept_code": "K3",
        "position_code": "K2",
        "cost_org_code": None,
        "manager_no": "E2001",
        "status": EmployeeStatus.PROBATION,
        "hire_date": date(2026, 9, 15),
        "contract_type": ContractType.INTERN,
        "daily_hours": Decimal("4.00"),
        "monthly_rest": 8,
        "confidentiality_level": 1,
    },
    {
        "employee_no": "E2004",
        "name": "张军",
        "gender": Gender.MALE,
        "company_code": "C2",
        "dept_code": "K2",
        "position_code": "K1",
        "cost_org_code": "K2",
        "manager_no": "E2001",
        "status": EmployeeStatus.RESIGNED,
        "hire_date": date(2018, 9, 1),
        "resign_date": date(2024, 3, 31),
        "contract_type": ContractType.FULL_TIME,
        "daily_hours": Decimal("8.00"),
        "monthly_rest": 8,
        "confidentiality_level": 3,
    },
    # Attendance demo employees E101-E113, exactly as the fixture README
    # section 1 describes. E110/E111 share a name, E112 resigned before
    # September, and E113 joins mid-September.
    {
        "employee_no": "E101",
        "name": "冯芷茵",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P1",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2020, 4, 11),
    },
    {
        "employee_no": "E102",
        "name": "刘衍英",
        "company_code": "C4",
        "dept_code": "D2",
        "position_code": "P3",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2018, 9, 3),
    },
    {
        "employee_no": "E103",
        "name": "周玉琼",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P1",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2019, 3, 18),
    },
    {
        "employee_no": "E104",
        "name": "胡国邵",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P1",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2017, 6, 1),
    },
    {
        "employee_no": "E105",
        "name": "李金辉",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P1",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2021, 11, 8),
    },
    {
        "employee_no": "E106",
        "name": "黄佳誉",
        "company_code": "C4",
        "dept_code": "D3",
        "position_code": "P4",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2020, 2, 17),
    },
    {
        "employee_no": "E107",
        "name": "梁林高",
        "company_code": "C4",
        "dept_code": "D4",
        "position_code": "P5",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2016, 5, 23),
    },
    {
        "employee_no": "E108",
        "name": "黄国锋",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P2",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2019, 8, 30),
    },
    {
        "employee_no": "E109",
        "name": "申佳林",
        "company_code": "C4",
        "dept_code": "D4",
        "position_code": "P5",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2015, 10, 12),
    },
    {
        "employee_no": "E110",
        "name": "张伟",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P1",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2019, 1, 1),
    },
    {
        "employee_no": "E111",
        "name": "张伟",
        "company_code": "C4",
        "dept_code": "D2",
        "position_code": "P3",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2020, 1, 1),
    },
    {
        "employee_no": "E112",
        "name": "王强",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P1",
        "status": EmployeeStatus.RESIGNED,
        "hire_date": date(2018, 1, 1),
        "resign_date": date(2026, 8, 31),
    },
    {
        "employee_no": "E113",
        "name": "李娜",
        "company_code": "C4",
        "dept_code": "D1",
        "position_code": "P1",
        "status": EmployeeStatus.ACTIVE,
        "hire_date": date(2026, 9, 15),
    },
]


# Attendance reference data for the C4 demo company. Plans, roster entries,
# and import batches are added by later slices through the real service paths.
SHIFTS: list[dict[str, Any]] = [
    {
        "company_code": "C4",
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
        "company_code": "C4",
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
        "company_code": "C4",
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
        "company_code": "C4",
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
        "company_code": "C4",
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
        "company_code": "C4",
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
        "company_code": "C4",
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
        "company_code": "C4",
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
        "company_code": "C4",
        "date": date(2026, 9, 25),
        "name": "中秋节",
        "day_type": HolidayDayType.HOLIDAY,
    },
    {
        "company_code": "C4",
        "date": date(2026, 9, 27),
        "name": "调休上班",
        "day_type": HolidayDayType.ADJUSTED_WORKDAY,
    },
    *[
        {
            "company_code": "C4",
            "date": date(2026, 10, day),
            "name": "国庆节",
            "day_type": HolidayDayType.HOLIDAY,
        }
        for day in range(1, 8)
    ],
]


# Four 2026-09 plans from spec section 15.3. ``weekdays`` maps Monday=0 …
# Sunday=6 to shift codes; ``day_overrides`` adds adjusted workdays and the
# employee plan's 09-30 night shift.
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
ATTENDANCE_PLANS: list[dict[str, Any]] = [
    {
        "company_code": "C4",
        "month": date(2026, 9, 1),
        "plan_name": "行政班",
        "scope_type": ScheduleScopeType.ALL,
        "scope_dept_codes": [],
        "scope_position_codes": [],
        "scope_employee_nos": [],
        "weekdays": WEEKDAY_ADM,
        "day_overrides": {27: ["ADM"]},
        "rule_overrides": None,
        "note": "全公司兜底方案；09-27 调休上班",
    },
    {
        "company_code": "C4",
        "month": date(2026, 9, 1),
        "plan_name": "财务技术班",
        "scope_type": ScheduleScopeType.DEPT,
        "scope_dept_codes": ["D2"],
        "scope_position_codes": [],
        "scope_employee_nos": [],
        "weekdays": WEEKDAY_TEC,
        "day_overrides": {27: ["TEC"]},
        "rule_overrides": None,
        "note": "财务部固定技术员班；09-27 调休上班",
    },
    {
        "company_code": "C4",
        "month": date(2026, 9, 1),
        "plan_name": "园林班",
        "scope_type": ScheduleScopeType.POSITION,
        "scope_dept_codes": [],
        "scope_position_codes": ["P2"],
        "scope_employee_nos": [],
        "weekdays": WEEKDAY_YL,
        "day_overrides": {27: ["YL"]},
        "rule_overrides": {"ot_threshold_min": 15},
        "note": "园林工岗位方案；加班起算门槛覆盖为 15 分钟",
    },
    {
        "company_code": "C4",
        "month": date(2026, 9, 1),
        "plan_name": "李金辉夜班",
        "scope_type": ScheduleScopeType.EMPLOYEE,
        "scope_dept_codes": [],
        "scope_position_codes": [],
        "scope_employee_nos": ["E105"],
        "weekdays": WEEKDAY_ADM,
        "day_overrides": {30: ["NIGHT"]},
        "rule_overrides": None,
        "note": "员工级方案：工作日行政班，09-30 夜班",
    },
]


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


def _seed_employees(session: Session, companies: dict[str, Company]) -> None:
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

    for data in EMPLOYEES:
        if data["employee_no"] in employees:
            continue

        # Required keys fail fast. Gender, cost center, manager, and contract
        # type are optional in the model, so the attendance demo may omit them.
        for required_key in (
            "employee_no",
            "name",
            "company_code",
            "dept_code",
            "position_code",
            "status",
            "hire_date",
        ):
            if required_key not in data:
                raise KeyError(
                    f"Seed employee {data.get('employee_no', '?')} is missing "
                    f"{required_key}"
                )

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


def _seed_attendance_plans(
    session: Session,
    companies: dict[str, Company],
    departments: dict[tuple[Any, str], Department],
) -> None:
    """Insert the four 2026-09 plans and expand them once.

    Expansion goes through the real service path so the demo roster matches
    what the API would produce. Existing plans are never overwritten, and a
    second run does not re-expand the month.
    """
    company = companies["C4"]
    month = date(2026, 9, 1)
    existing = session.exec(
        select(SchedulePlan).where(
            col(SchedulePlan.company_id) == company.id,
            col(SchedulePlan.month) == month,
        )
    ).all()
    if existing:
        return

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
    employees = {
        employee.employee_no: employee
        for employee in session.exec(select(Employee)).all()
    }
    for data in ATTENDANCE_PLANS:
        plan = SchedulePlan(
            company_id=company.id,
            month=data["month"],
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
            session.add(
                PlanScope(
                    plan_id=plan.id,
                    scope_id=employees[employee_no].id,
                )
            )
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
    expansion.expand_month(session, company.id, month)
    session.flush()


def _seed_attendance_manual_entries(
    session: Session, companies: dict[str, Company]
) -> None:
    """Insert the two documented manual exceptions if they are missing.

    The rows go in after plan expansion so ``plan_id`` records the overridden
    plan. A second run never overwrites a user-edited exception.
    """
    company = companies["C4"]
    month = date(2026, 9, 1)
    employees = {
        employee.employee_no: employee
        for employee in session.exec(
            select(Employee).where(col(Employee.employee_no).in_(["E103", "E104"]))
        ).all()
    }
    shifts = {
        shift.shift_code: shift
        for shift in session.exec(
            select(Shift).where(col(Shift.company_id) == company.id)
        ).all()
    }
    candidates = expansion.load_candidates(session, company.id, month)
    seeds: list[tuple[str, date, RosterState, list[str], str | None]] = [
        ("E103", date(2026, 9, 10), RosterState.REST, [], "个人调休"),
        ("E104", date(2026, 9, 11), RosterState.WORK, ["EARLY", "MID"], "临时双班"),
    ]
    for employee_no, work_date, state, shift_codes, note in seeds:
        employee = employees.get(employee_no)
        if employee is None:
            continue
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
            # Convert the plan row the expansion just created.
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


def seed(session: Session) -> None:
    companies = _seed_companies(session)
    departments = _seed_departments(session, companies)
    _seed_positions(session, companies, departments)
    _seed_cost_centers(session, companies)
    _seed_employees(session, companies)
    _seed_shifts(session, companies)
    _seed_attendance_rules(session, companies)
    _seed_holidays(session, companies)
    _seed_attendance_plans(session, companies, departments)
    _seed_attendance_manual_entries(session, companies)
    session.commit()


def main() -> None:
    if settings.FASTAPI_ENV != "development":
        raise SystemExit("Refusing to seed: FASTAPI_ENV must be 'development'.")
    with Session(engine) as session:
        seed(session)
    logger.info("Development seed data is up to date")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
