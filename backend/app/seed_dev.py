"""Development-only seed data.

Run manually from the backend directory with ``uv run python -m app.seed_dev``.
The script refuses to run unless ``FASTAPI_ENV=development`` and only inserts
rows that are missing by business code, so user edits are never overwritten.
"""

import logging
from decimal import Decimal
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import Company, CostCenter, Department, Position

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


def seed(session: Session) -> None:
    companies = _seed_companies(session)
    departments = _seed_departments(session, companies)
    _seed_positions(session, companies, departments)
    _seed_cost_centers(session, companies)
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
