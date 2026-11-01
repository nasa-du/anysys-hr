"""Factories for Basic Management test data.

Each factory commits and refreshes the row so tests can use ids and generated
fields immediately. Factories only build database state; business rules are
exercised through the service/API layer instead.
"""

from datetime import date
from decimal import Decimal

from sqlmodel import Session, SQLModel

from app.enums import ContractType, EmployeeStatus, Gender
from app.models import Company, CostCenter, Department, Employee, Position
from tests.utils.utils import random_upper_code


def _persist[ModelT: SQLModel](db: Session, entity: ModelT) -> ModelT:
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def create_company(
    db: Session,
    *,
    company_code: str | None = None,
    company_name: str | None = None,
    is_active: bool = True,
    note: str | None = None,
) -> Company:
    company = Company(
        company_code=company_code or random_upper_code("C"),
        company_name=company_name or "荣新建设",
        is_active=is_active,
        note=note,
    )
    return _persist(db, company)


def create_department(
    db: Session,
    *,
    company: Company,
    dept_code: str | None = None,
    dept_name: str | None = None,
    parent: Department | None = None,
    manager: Employee | None = None,
    order_no: int = 0,
    is_active: bool = True,
    note: str | None = None,
) -> Department:
    department = Department(
        dept_code=dept_code or random_upper_code("D"),
        dept_name=dept_name or "生产部",
        company_id=company.id,
        parent_id=parent.id if parent else None,
        manager_id=manager.id if manager else None,
        order_no=order_no,
        is_active=is_active,
        note=note,
    )
    return _persist(db, department)


def create_position(
    db: Session,
    *,
    company: Company,
    position_code: str | None = None,
    position_name: str | None = None,
    dept: Department | None = None,
    order_no: int = 0,
    is_active: bool = True,
    note: str | None = None,
) -> Position:
    position = Position(
        position_code=position_code or random_upper_code("P"),
        position_name=position_name or "项目经理",
        company_id=company.id,
        dept_id=dept.id if dept else None,
        order_no=order_no,
        is_active=is_active,
        note=note,
    )
    return _persist(db, position)


def create_cost_center(
    db: Session,
    *,
    company: Company,
    cost_org_code: str | None = None,
    cost_org_name: str | None = None,
    parent: CostCenter | None = None,
    manager: Employee | None = None,
    budget: Decimal = Decimal("0"),
    warn_pct: int = 85,
    order_no: int = 0,
    is_active: bool = True,
    note: str | None = None,
) -> CostCenter:
    cost_center = CostCenter(
        cost_org_code=cost_org_code or random_upper_code("K"),
        cost_org_name=cost_org_name or "生产成本中心",
        company_id=company.id,
        parent_id=parent.id if parent else None,
        manager_id=manager.id if manager else None,
        budget=budget,
        warn_pct=warn_pct,
        order_no=order_no,
        is_active=is_active,
        note=note,
    )
    return _persist(db, cost_center)


def create_employee(
    db: Session,
    *,
    dept: Department,
    position: Position,
    employee_no: str | None = None,
    name: str | None = None,
    gender: Gender | None = None,
    cost_org: CostCenter | None = None,
    manager: Employee | None = None,
    status: EmployeeStatus = EmployeeStatus.ACTIVE,
    hire_date: date | None = None,
    resign_date: date | None = None,
    contract_type: ContractType = ContractType.FULL_TIME,
    daily_hours: Decimal | None = None,
    monthly_rest: int | None = None,
    confidentiality_level: int | None = None,
    note: str | None = None,
) -> Employee:
    effective_hire_date = hire_date or date.today()
    if status is EmployeeStatus.RESIGNED and resign_date is None:
        resign_date = effective_hire_date

    employee = Employee(
        employee_no=employee_no or random_upper_code("E"),
        name=name or "张三",
        gender=gender,
        dept_id=dept.id,
        position_id=position.id,
        cost_org_id=cost_org.id if cost_org else None,
        manager_id=manager.id if manager else None,
        status=status,
        hire_date=effective_hire_date,
        resign_date=resign_date,
        contract_type=contract_type,
        daily_hours=daily_hours,
        monthly_rest=monthly_rest,
        confidentiality_level=confidentiality_level,
        note=note,
    )
    return _persist(db, employee)
