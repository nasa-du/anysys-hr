"""Development seed script: guard and idempotency."""

from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app import seed_dev
from app.core.db import engine
from app.enums import EmployeeStatus
from app.models import Company, CostCenter, Department, Employee, Position

SEEDED_CODES = ["C1", "C2", "C3"]
SEEDED_NAMES = ["荣新建设", "荣新科技", "荣新物流"]
SEEDED_DEPARTMENTS = {
    "C1": ["D1", "D2", "D3", "D4", "D5", "D6", "D7"],
    "C2": ["K1", "K2", "K3"],
    "C3": [],
}
SEEDED_POSITIONS = {
    "C1": ["P1", "P2", "P3", "P4", "P5", "P6"],
    "C2": ["K1", "K2"],
    "C3": [],
}
SEEDED_COST_CENTERS = {
    "C1": ["K1", "K2", "K3", "K4", "K5", "K6"],
    "C2": ["K1", "K2"],
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


def _positions_by_company() -> dict[str, list[Position]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        positions: dict[str, list[Position]] = {
            code: [] for code in company_codes.values()
        }
        for position in session.exec(
            select(Position).order_by(Position.position_code)
        ).all():
            positions[company_codes[position.company_id]].append(position)
        return positions


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


def test_seed_inserts_positions_once() -> None:
    seed_dev.main()
    seed_dev.main()

    positions = _positions_by_company()

    for company_code, expected_codes in SEEDED_POSITIONS.items():
        assert [p.position_code for p in positions[company_code]] == expected_codes

    full_company = {p.position_code: p for p in positions["C1"]}
    assert full_company["P1"].dept_id is not None
    assert full_company["P2"].dept_id is not None
    assert full_company["P6"].dept_id is None
    assert all(p.is_active for p in positions["C1"])


def test_seed_position_default_departments_use_the_same_company() -> None:
    seed_dev.main()

    with Session(engine) as session:
        departments = {
            department.id: department
            for department in session.exec(select(Department)).all()
        }
        positions = session.exec(select(Position)).all()

        for position in positions:
            if position.dept_id is None:
                continue
            assert departments[position.dept_id].company_id == position.company_id


def test_seed_does_not_overwrite_existing_position_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        position = session.exec(
            select(Position).where(Position.position_code == "P1")
        ).one()
        position.position_name = "用户修改后的岗位"
        position.order_no = 42
        session.add(position)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        position = session.exec(
            select(Position).where(Position.position_code == "P1")
        ).one()
        assert position.position_name == "用户修改后的岗位"
        assert position.order_no == 42


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


def _cost_centers_by_company() -> dict[str, list[CostCenter]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        cost_centers: dict[str, list[CostCenter]] = {
            code: [] for code in company_codes.values()
        }
        for cost_center in session.exec(
            select(CostCenter).order_by(CostCenter.cost_org_code)
        ).all():
            cost_centers[company_codes[cost_center.company_id]].append(cost_center)
        return cost_centers


def test_seed_inserts_the_cost_center_tree_once() -> None:
    seed_dev.main()
    seed_dev.main()

    cost_centers = _cost_centers_by_company()

    for company_code, expected_codes in SEEDED_COST_CENTERS.items():
        assert [c.cost_org_code for c in cost_centers[company_code]] == expected_codes

    full_company = {c.cost_org_code: c for c in cost_centers["C1"]}
    assert full_company["K1"].parent_id is None
    assert full_company["K2"].parent_id == full_company["K1"].id
    assert full_company["K3"].parent_id == full_company["K2"].id
    assert full_company["K4"].parent_id == full_company["K2"].id
    assert full_company["K5"].parent_id == full_company["K1"].id
    assert full_company["K6"].parent_id == full_company["K1"].id
    assert full_company["K6"].is_active is False
    assert all(c.is_active for c in cost_centers["C2"])


def test_seed_includes_one_inactive_cost_center_without_active_employees() -> None:
    seed_dev.main()

    with Session(engine) as session:
        inactive_cost_centers = session.exec(
            select(CostCenter).where(CostCenter.is_active.is_(False))
        ).all()
        inactive_ids = [cost_center.id for cost_center in inactive_cost_centers]
        active_employees = session.exec(
            select(Employee).where(
                Employee.cost_org_id.in_(inactive_ids),
                Employee.status.in_([EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION]),
            )
        ).all()

    assert [c.cost_org_code for c in inactive_cost_centers] == ["K6"]
    assert active_employees == []


def test_seed_cost_center_parents_and_budgets_use_the_same_company() -> None:
    seed_dev.main()

    with Session(engine) as session:
        cost_centers = {
            cost_center.id: cost_center
            for cost_center in session.exec(select(CostCenter)).all()
        }

        for cost_center in cost_centers.values():
            assert cost_center.budget >= 0
            assert 1 <= cost_center.warn_pct <= 100
            if cost_center.parent_id is None:
                continue
            parent = cost_centers[cost_center.parent_id]
            assert parent.company_id == cost_center.company_id


def test_seed_does_not_overwrite_existing_cost_center_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        cost_center = session.exec(
            select(CostCenter).where(
                CostCenter.company_id == company.id,
                CostCenter.cost_org_code == "K2",
            )
        ).one()
        cost_center.cost_org_name = "用户修改后的成本中心"
        cost_center.budget = Decimal("42.00")
        cost_center.warn_pct = 66
        session.add(cost_center)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        cost_center = session.exec(
            select(CostCenter).where(
                CostCenter.company_id == company.id,
                CostCenter.cost_org_code == "K2",
            )
        ).one()
        assert cost_center.cost_org_name == "用户修改后的成本中心"
        assert cost_center.budget == Decimal("42.00")
        assert cost_center.warn_pct == 66
