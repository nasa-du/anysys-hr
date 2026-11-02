"""Development-only seed data.

Run manually from the backend directory with ``uv run python -m app.seed_dev``.
The script refuses to run unless ``FASTAPI_ENV=development`` and only inserts
rows that are missing by business code, so user edits are never overwritten.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.enums import ContractType, EmployeeStatus, Gender
from app.models import Company, CostCenter, Department, Employee, Position

logger = logging.getLogger(__name__)

COMPANIES: list[dict[str, Any]] = [
    {"company_code": "C1", "company_name": "荣新建设", "note": "完整组织示例"},
    {"company_code": "C2", "company_name": "荣新科技", "note": "小型组织示例"},
    {"company_code": "C3", "company_name": "荣新物流", "note": "空公司示例"},
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
        cost_org_code = data["cost_org_code"]
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
        manager_no = data["manager_no"]
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
            gender=data["gender"],
            dept_id=department.id,
            position_id=position.id,
            cost_org_id=cost_org_id,
            manager_id=manager_id,
            status=data["status"],
            hire_date=data["hire_date"],
            resign_date=data.get("resign_date"),
            contract_type=data["contract_type"],
            daily_hours=data.get("daily_hours"),
            monthly_rest=data.get("monthly_rest"),
            confidentiality_level=data.get("confidentiality_level"),
            note=data.get("note"),
        )
        session.add(employee)
        session.flush()
        employees[employee.employee_no] = employee


def seed(session: Session) -> None:
    companies = _seed_companies(session)
    departments = _seed_departments(session, companies)
    _seed_positions(session, companies, departments)
    _seed_cost_centers(session, companies)
    _seed_employees(session, companies)
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
