import re
from datetime import date
from decimal import Decimal

from sqlmodel import Session

from app.enums import ContractType, EmployeeStatus
from app.models import Company, Department, Employee, Position
from tests.utils.factories import (
    create_company,
    create_cost_center,
    create_department,
    create_employee,
    create_position,
)

CODE_PATTERN = re.compile(r"[A-Z0-9_-]{1,32}")


def test_company_factory_persists_contract_defaults(db: Session) -> None:
    company = create_company(db)
    stored = db.get(Company, company.id)

    assert stored is not None
    assert stored.is_active is True
    assert stored.note is None
    assert stored.id.version == 7
    assert stored.created_at.tzinfo is not None
    assert stored.updated_at.tzinfo is not None
    assert CODE_PATTERN.fullmatch(stored.company_code)


def test_factories_build_a_consistent_organization_graph(db: Session) -> None:
    company = create_company(db)
    root = create_department(db, company=company, dept_name="总部")
    child = create_department(db, company=company, parent=root)
    position = create_position(db, company=company, dept=child)
    cost_center = create_cost_center(db, company=company)
    manager = create_employee(db, dept=child, position=position, name="李四")
    report = create_employee(
        db,
        dept=child,
        position=position,
        cost_org=cost_center,
        manager=manager,
    )

    assert root.company_id == company.id
    assert child.parent_id == root.id
    assert child.company_id == company.id
    assert position.company_id == company.id
    assert position.dept_id == child.id
    assert cost_center.company_id == company.id
    assert manager.dept_id == child.id
    assert manager.position_id == position.id
    assert report.manager_id == manager.id
    assert report.cost_org_id == cost_center.id
    assert report.id.version == 7
    assert db.get(Employee, report.id) is not None
    assert db.get(Department, child.id) is not None
    assert db.get(Position, position.id) is not None


def test_factories_generate_unique_codes(db: Session) -> None:
    company = create_company(db)
    companies = [create_company(db) for _ in range(5)]
    departments = [create_department(db, company=company) for _ in range(5)]
    positions = [create_position(db, company=company) for _ in range(5)]
    cost_centers = [create_cost_center(db, company=company) for _ in range(5)]
    employees = [
        create_employee(db, dept=departments[0], position=positions[0])
        for _ in range(5)
    ]

    assert len({item.company_code for item in companies}) == 5
    assert len({item.dept_code for item in departments}) == 5
    assert len({item.position_code for item in positions}) == 5
    assert len({item.cost_org_code for item in cost_centers}) == 5
    assert len({item.employee_no for item in employees}) == 5


def test_employee_factory_supports_the_employee_profile(db: Session) -> None:
    company = create_company(db)
    dept = create_department(db, company=company)
    position = create_position(db, company=company)
    hire_date = date(2025, 1, 6)
    resign_date = date(2025, 12, 31)

    employee = create_employee(
        db,
        dept=dept,
        position=position,
        status=EmployeeStatus.RESIGNED,
        hire_date=hire_date,
        resign_date=resign_date,
        contract_type=ContractType.PART_TIME,
        daily_hours=Decimal("4.00"),
        monthly_rest=8,
        confidentiality_level=2,
    )

    assert employee.status is EmployeeStatus.RESIGNED
    assert employee.hire_date == hire_date
    assert employee.resign_date == resign_date
    assert employee.contract_type is ContractType.PART_TIME
    assert employee.daily_hours == Decimal("4.00")
    assert employee.monthly_rest == 8
    assert employee.confidentiality_level == 2


def test_resigned_employee_factory_defaults_the_resign_date(
    db: Session,
) -> None:
    company = create_company(db)
    dept = create_department(db, company=company)
    position = create_position(db, company=company)
    hire_date = date(2025, 1, 6)

    employee = create_employee(
        db,
        dept=dept,
        position=position,
        status=EmployeeStatus.RESIGNED,
        hire_date=hire_date,
    )

    assert employee.resign_date == hire_date
