"""Development-only seed data.

Run manually from the backend directory with ``uv run python -m app.seed_dev``.
The script refuses to run unless ``FASTAPI_ENV=development`` and only inserts
rows that are missing by business code, so user edits are never overwritten.
"""

import logging
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import Company, Department

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


def _seed_departments(session: Session, companies: dict[str, Company]) -> None:
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


def seed(session: Session) -> None:
    companies = _seed_companies(session)
    _seed_departments(session, companies)
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
