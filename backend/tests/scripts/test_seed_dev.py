"""Development seed script: guard and idempotency."""

import pytest
from sqlmodel import Session, select

from app import seed_dev
from app.core.db import engine
from app.enums import EmployeeStatus
from app.models import Company, Department, Employee

SEEDED_CODES = ["C1", "C2", "C3"]
SEEDED_NAMES = ["荣新建设", "荣新科技", "荣新物流"]
SEEDED_DEPARTMENTS = {
    "C1": ["D1", "D2", "D3", "D4", "D5", "D6", "D7"],
    "C2": ["K1", "K2", "K3"],
    "C3": [],
}


def _companies() -> list[Company]:
    with Session(engine) as session:
        return list(session.exec(select(Company).order_by(Company.company_code)).all())


def _departments_by_company() -> dict[str, list[Department]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        departments: dict[str, list[Department]] = {
            code: [] for code in company_codes.values()
        }
        for department in session.exec(
            select(Department).order_by(Department.dept_code)
        ).all():
            departments[company_codes[department.company_id]].append(department)
        return departments


@pytest.mark.parametrize("environment", ["production", None])
def test_seed_refuses_outside_development(
    monkeypatch: pytest.MonkeyPatch, environment: str | None
) -> None:
    monkeypatch.setattr(seed_dev.settings, "FASTAPI_ENV", environment)

    with pytest.raises(SystemExit, match="development"):
        seed_dev.main()

    assert _companies() == []


def test_seed_inserts_three_companies_once() -> None:
    seed_dev.main()
    seed_dev.main()

    companies = _companies()
    assert [company.company_code for company in companies] == SEEDED_CODES
    assert [company.company_name for company in companies] == SEEDED_NAMES
    assert all(company.is_active for company in companies)


def test_seed_does_not_overwrite_existing_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        company.company_name = "用户修改后的名称"
        company.note = "用户备注"
        session.add(company)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        assert company.company_name == "用户修改后的名称"
        assert company.note == "用户备注"


def test_seed_inserts_the_department_tree_once() -> None:
    seed_dev.main()
    seed_dev.main()

    departments = _departments_by_company()

    for company_code, expected_codes in SEEDED_DEPARTMENTS.items():
        assert [d.dept_code for d in departments[company_code]] == expected_codes

    full_company = {d.dept_code: d for d in departments["C1"]}
    assert full_company["D2"].parent_id == full_company["D1"].id
    assert full_company["D3"].parent_id == full_company["D2"].id
    assert full_company["D4"].parent_id == full_company["D2"].id
    assert full_company["D1"].parent_id is None


def test_seed_includes_one_inactive_department_without_active_employees() -> None:
    seed_dev.main()

    with Session(engine) as session:
        inactive_departments = session.exec(
            select(Department).where(Department.is_active.is_(False))
        ).all()
        inactive_ids = [department.id for department in inactive_departments]
        active_employees = session.exec(
            select(Employee).where(
                Employee.dept_id.in_(inactive_ids),
                Employee.status.in_([EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION]),
            )
        ).all()

    assert [department.dept_code for department in inactive_departments] == ["D7"]
    assert active_employees == []


def test_seed_does_not_overwrite_existing_department_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        department = session.exec(
            select(Department).where(Department.dept_code == "D2")
        ).one()
        department.dept_name = "用户修改后的部门"
        department.order_no = 42
        session.add(department)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        department = session.exec(
            select(Department).where(Department.dept_code == "D2")
        ).one()
        assert department.dept_name == "用户修改后的部门"
        assert department.order_no == 42
