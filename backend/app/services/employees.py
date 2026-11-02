"""Employee business rules: records, assignments, managers, and lifecycle."""

import uuid
from collections import defaultdict
from typing import Any

from fastapi.exceptions import RequestValidationError
from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import EmployeeStatus
from app.models import (
    Company,
    CostCenter,
    Department,
    Employee,
    Position,
    get_datetime_utc,
)
from app.schemas_basic import (
    EmployeeCreate,
    EmployeePublic,
    EmployeesPublic,
    EmployeeUpdate,
)
from app.services.common import ACTIVE_EMPLOYEE_STATUSES, paginate

EMPLOYEE_NOT_FOUND_MESSAGE = "员工不存在"
COMPANY_NOT_FOUND_MESSAGE = "公司不存在"
DEPARTMENT_NOT_FOUND_MESSAGE = "部门不存在"
POSITION_NOT_FOUND_MESSAGE = "岗位不存在"
COST_CENTER_NOT_FOUND_MESSAGE = "成本中心不存在"
MANAGER_NOT_FOUND_MESSAGE = "直属上级不存在"
DUPLICATE_NO_MESSAGE = "工号已存在"
CYCLE_MESSAGE = "直属上级不能是本人或形成汇报环"
MANAGER_INACTIVE_MESSAGE = "直属上级必须是在职或试用期员工"
UNASSIGNED_CONFLICT_MESSAGE = "未分配成本中心与指定成本中心不能同时使用"

# A resignation request may only carry these fields; anything else is locked.
# Correcting an already-resigned employee uses the same fields, but the status
# may only remain ``resigned``.
RESIGNATION_FIELDS = frozenset({"status", "resign_date", "note"})
RESIGNED_CORRECTION_FIELDS = RESIGNATION_FIELDS


def _field_error(code: str, field: str, message: str) -> DomainError:
    return DomainError(code, message, field_errors={field: message})


def _duplicate_no_error() -> DomainError:
    return DomainError(
        "duplicate_code",
        DUPLICATE_NO_MESSAGE,
        field_errors={"employee_no": DUPLICATE_NO_MESSAGE},
    )


def _locked_field_error(fields: set[str], message: str) -> DomainError:
    return DomainError(
        "locked_field",
        message,
        field_errors=dict.fromkeys(sorted(fields), message),
    )


def get_employee_or_404(session: Session, employee_id: uuid.UUID) -> Employee:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise DomainError("not_found", EMPLOYEE_NOT_FOUND_MESSAGE)
    return employee


def _manager_company_id(session: Session, manager: Employee) -> uuid.UUID | None:
    department = session.get(Department, manager.dept_id)
    return department.company_id if department is not None else None


def _validate_department(
    session: Session, *, company_id: uuid.UUID, dept_id: uuid.UUID
) -> Department:
    department = session.get(Department, dept_id)
    if department is None:
        raise _field_error("invalid_reference", "dept_id", DEPARTMENT_NOT_FOUND_MESSAGE)
    if department.company_id != company_id:
        raise _field_error("cross_company", "dept_id", "部门必须属于同一公司")
    if not department.is_active:
        raise _field_error("inactive_reference", "dept_id", "部门已停用")
    return department


def _validate_position(
    session: Session, *, company_id: uuid.UUID, position_id: uuid.UUID
) -> None:
    position = session.get(Position, position_id)
    if position is None:
        raise _field_error(
            "invalid_reference", "position_id", POSITION_NOT_FOUND_MESSAGE
        )
    if position.company_id != company_id:
        raise _field_error("cross_company", "position_id", "岗位必须属于同一公司")
    if not position.is_active:
        raise _field_error("inactive_reference", "position_id", "岗位已停用")


def _validate_cost_center(
    session: Session, *, company_id: uuid.UUID, cost_org_id: uuid.UUID
) -> None:
    cost_center = session.get(CostCenter, cost_org_id)
    if cost_center is None:
        raise _field_error(
            "invalid_reference", "cost_org_id", COST_CENTER_NOT_FOUND_MESSAGE
        )
    if cost_center.company_id != company_id:
        raise _field_error("cross_company", "cost_org_id", "成本中心必须属于同一公司")
    if not cost_center.is_active:
        raise _field_error("inactive_reference", "cost_org_id", "成本中心已停用")


def _creates_reporting_cycle(
    session: Session, *, employee_id: uuid.UUID, manager: Employee
) -> bool:
    """Walk up from the candidate manager; hitting the employee closes a cycle."""
    current: Employee | None = manager
    seen: set[uuid.UUID] = set()
    while current is not None:
        if current.id == employee_id or current.id in seen:
            return True
        seen.add(current.id)
        current = (
            session.get(Employee, current.manager_id) if current.manager_id else None
        )
    return False


def _validate_manager(
    session: Session,
    *,
    company_id: uuid.UUID,
    manager_id: uuid.UUID,
    employee_id: uuid.UUID | None,
) -> None:
    manager = session.get(Employee, manager_id)
    if manager is None:
        raise _field_error("invalid_reference", "manager_id", MANAGER_NOT_FOUND_MESSAGE)
    if _manager_company_id(session, manager) != company_id:
        raise _field_error("cross_company", "manager_id", "直属上级必须属于同一公司")
    if manager.status not in ACTIVE_EMPLOYEE_STATUSES:
        raise _field_error("inactive_reference", "manager_id", MANAGER_INACTIVE_MESSAGE)
    if employee_id is not None and (
        manager.id == employee_id
        or _creates_reporting_cycle(session, employee_id=employee_id, manager=manager)
    ):
        raise _field_error("cycle", "manager_id", CYCLE_MESSAGE)


def _to_public(
    employee: Employee,
    departments: dict[uuid.UUID, Department],
    companies: dict[uuid.UUID, Company],
    positions: dict[uuid.UUID, Position],
    cost_centers: dict[uuid.UUID, CostCenter],
    managers: dict[uuid.UUID, Employee],
) -> EmployeePublic:
    department = departments[employee.dept_id]
    company = companies[department.company_id]
    position = positions[employee.position_id]
    cost_center = (
        cost_centers.get(employee.cost_org_id) if employee.cost_org_id else None
    )
    manager = managers.get(employee.manager_id) if employee.manager_id else None
    return EmployeePublic(
        id=employee.id,
        employee_no=employee.employee_no,
        name=employee.name,
        gender=employee.gender,
        dept_id=employee.dept_id,
        position_id=employee.position_id,
        cost_org_id=employee.cost_org_id,
        manager_id=employee.manager_id,
        status=employee.status,
        hire_date=employee.hire_date,
        resign_date=employee.resign_date,
        contract_type=employee.contract_type,
        daily_hours=employee.daily_hours,
        monthly_rest=employee.monthly_rest,
        confidentiality_level=employee.confidentiality_level,
        note=employee.note,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
        company_id=company.id,
        company_name=company.company_name,
        dept_name=department.dept_name,
        position_name=position.position_name,
        cost_org_name=cost_center.cost_org_name if cost_center else None,
        manager_name=manager.name if manager else None,
        manager_status=manager.status if manager else None,
    )


def _public_many(session: Session, employees: list[Employee]) -> list[EmployeePublic]:
    if not employees:
        return []

    dept_ids = {employee.dept_id for employee in employees}
    position_ids = {employee.position_id for employee in employees}
    cost_org_ids = {
        employee.cost_org_id
        for employee in employees
        if employee.cost_org_id is not None
    }
    manager_ids = {
        employee.manager_id for employee in employees if employee.manager_id is not None
    }

    departments = {
        department.id: department
        for department in session.exec(
            select(Department).where(col(Department.id).in_(dept_ids))
        ).all()
    }
    companies = {
        company.id: company
        for company in session.exec(
            select(Company).where(
                col(Company.id).in_(
                    {department.company_id for department in departments.values()}
                )
            )
        ).all()
    }
    positions = {
        position.id: position
        for position in session.exec(
            select(Position).where(col(Position.id).in_(position_ids))
        ).all()
    }
    cost_centers = {
        cost_center.id: cost_center
        for cost_center in session.exec(
            select(CostCenter).where(col(CostCenter.id).in_(cost_org_ids))
        ).all()
    }
    managers = {
        manager.id: manager
        for manager in session.exec(
            select(Employee).where(col(Employee.id).in_(manager_ids))
        ).all()
    }
    return [
        _to_public(employee, departments, companies, positions, cost_centers, managers)
        for employee in employees
    ]


def _public_one(session: Session, employee: Employee) -> EmployeePublic:
    return _public_many(session, [employee])[0]


def get_employee(session: Session, employee_id: uuid.UUID) -> EmployeePublic:
    """Return one employee with its display fields resolved."""
    return _public_one(session, get_employee_or_404(session, employee_id))


def _descendant_department_ids(
    session: Session, department: Department
) -> set[uuid.UUID]:
    """The department and every descendant, scoped to its company."""
    departments = session.exec(
        select(Department).where(col(Department.company_id) == department.company_id)
    ).all()
    children: dict[uuid.UUID | None, list[uuid.UUID]] = defaultdict(list)
    for item in departments:
        children[item.parent_id].append(item.id)

    ids = {department.id}
    pending = [department.id]
    while pending:
        for child_id in children.get(pending.pop(), []):
            if child_id not in ids:
                ids.add(child_id)
                pending.append(child_id)
    return ids


def list_employees(
    session: Session,
    *,
    company_id: uuid.UUID | None,
    dept_id: uuid.UUID | None,
    position_id: uuid.UUID | None,
    cost_org_id: uuid.UUID | None,
    unassigned_cost_org: bool,
    statuses: list[EmployeeStatus] | None,
    keyword: str | None,
    skip: int,
    limit: int,
) -> EmployeesPublic:
    if unassigned_cost_org and cost_org_id is not None:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("query", "unassigned_cost_org"),
                    "msg": f"Value error, {UNASSIGNED_CONFLICT_MESSAGE}",
                    "input": unassigned_cost_org,
                }
            ]
        )

    filters: list[ColumnElement[bool]] = []

    if company_id is not None:
        if session.get(Company, company_id) is None:
            raise DomainError("not_found", COMPANY_NOT_FOUND_MESSAGE)
        filters.append(
            col(Employee.dept_id).in_(
                select(Department.id).where(col(Department.company_id) == company_id)
            )
        )

    if dept_id is not None:
        department = session.get(Department, dept_id)
        if department is None:
            raise DomainError("not_found", DEPARTMENT_NOT_FOUND_MESSAGE)
        filters.append(
            col(Employee.dept_id).in_(_descendant_department_ids(session, department))
        )

    if position_id is not None:
        if session.get(Position, position_id) is None:
            raise DomainError("not_found", POSITION_NOT_FOUND_MESSAGE)
        filters.append(col(Employee.position_id) == position_id)

    if cost_org_id is not None:
        if session.get(CostCenter, cost_org_id) is None:
            raise DomainError("not_found", COST_CENTER_NOT_FOUND_MESSAGE)
        filters.append(col(Employee.cost_org_id) == cost_org_id)

    if unassigned_cost_org:
        filters.append(col(Employee.cost_org_id).is_(None))

    effective_statuses = (
        list(statuses) if statuses is not None else list(ACTIVE_EMPLOYEE_STATUSES)
    )
    filters.append(col(Employee.status).in_(effective_statuses))

    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        filters.append(
            or_(
                col(Employee.employee_no).ilike(pattern),
                col(Employee.name).ilike(pattern),
            )
        )

    statement = (
        select(Employee)
        .where(*filters)
        .order_by(col(Employee.employee_no).asc(), col(Employee.name).asc())
    )
    count_statement = select(func.count()).select_from(Employee).where(*filters)
    items, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return EmployeesPublic(data=_public_many(session, items), count=count)


def create_employee(session: Session, payload: EmployeeCreate) -> EmployeePublic:
    department = session.get(Department, payload.dept_id)
    if department is None:
        raise _field_error("invalid_reference", "dept_id", DEPARTMENT_NOT_FOUND_MESSAGE)
    if not department.is_active:
        raise _field_error("inactive_reference", "dept_id", "部门已停用")
    company_id = department.company_id

    if payload.status is EmployeeStatus.RESIGNED:
        raise _field_error(
            "invalid_status_transition",
            "status",
            "新建员工只能是在职或试用期状态",
        )

    existing = session.exec(
        select(Employee).where(Employee.employee_no == payload.employee_no)
    ).first()
    if existing is not None:
        raise _duplicate_no_error()

    _validate_position(session, company_id=company_id, position_id=payload.position_id)
    if payload.cost_org_id is not None:
        _validate_cost_center(
            session, company_id=company_id, cost_org_id=payload.cost_org_id
        )
    if payload.manager_id is not None:
        _validate_manager(
            session,
            company_id=company_id,
            manager_id=payload.manager_id,
            employee_id=None,
        )

    employee = Employee(
        employee_no=payload.employee_no,
        name=payload.name,
        gender=payload.gender,
        dept_id=payload.dept_id,
        position_id=payload.position_id,
        cost_org_id=payload.cost_org_id,
        manager_id=payload.manager_id,
        status=payload.status,
        hire_date=payload.hire_date,
        contract_type=payload.contract_type,
        daily_hours=payload.daily_hours,
        monthly_rest=payload.monthly_rest,
        confidentiality_level=payload.confidentiality_level,
        note=payload.note,
    )
    session.add(employee)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_no_error()
    session.refresh(employee)
    return _public_one(session, employee)


def _validate_status_machine(employee: Employee, data: dict[str, Any]) -> None:
    """Reject illegal transitions and locked fields on the final status."""
    current = employee.status
    has_status = "status" in data
    requested = data["status"] if has_status else current

    if current is EmployeeStatus.RESIGNED:
        if has_status and requested is not EmployeeStatus.RESIGNED:
            raise _field_error(
                "invalid_status_transition",
                "status",
                "离职为终态，不能恢复在职或试用期",
            )
        locked = {field for field in data if field not in RESIGNED_CORRECTION_FIELDS}
        if locked:
            raise _locked_field_error(locked, "离职员工只能修改备注和离职日期")
        if data.get("resign_date", employee.resign_date) is None:
            raise _field_error(
                "invalid_status_transition", "resign_date", "离职日期不能为空"
            )
        return

    if has_status and requested is EmployeeStatus.RESIGNED:
        locked = {field for field in data if field not in RESIGNATION_FIELDS}
        if locked:
            raise _locked_field_error(locked, "办理离职时只能修改状态、离职日期和备注")
        if data.get("resign_date") is None:
            raise _field_error(
                "invalid_status_transition", "resign_date", "离职必须填写离职日期"
            )
        return

    if (
        has_status
        and requested is EmployeeStatus.PROBATION
        and current is EmployeeStatus.ACTIVE
    ):
        raise _field_error(
            "invalid_status_transition", "status", "在职员工不能改为试用期"
        )

    if "resign_date" in data:
        raise _field_error(
            "invalid_status_transition", "resign_date", "非离职员工不能填写离职日期"
        )


def _validate_final_dates(
    employee: Employee, data: dict[str, Any], final_status: EmployeeStatus
) -> None:
    hire_date = data.get("hire_date", employee.hire_date)
    resign_date = data.get("resign_date", employee.resign_date)
    if final_status is EmployeeStatus.RESIGNED:
        if resign_date is None:
            raise _field_error(
                "invalid_status_transition", "resign_date", "离职必须填写离职日期"
            )
        if resign_date < hire_date:
            raise _field_error(
                "invalid_status_transition", "resign_date", "离职日期不能早于入职日期"
            )
    elif resign_date is not None:
        raise _field_error(
            "invalid_status_transition", "resign_date", "非离职员工不能填写离职日期"
        )


def update_employee(
    session: Session, employee_id: uuid.UUID, payload: EmployeeUpdate
) -> EmployeePublic:
    employee = get_employee_or_404(session, employee_id)
    data = payload.model_dump(exclude_unset=True)

    _validate_status_machine(employee, data)
    final_status = data.get("status", employee.status)
    _validate_final_dates(employee, data, final_status)

    # The company is derived from the department and cannot change.
    current_department = session.get(Department, employee.dept_id)
    if current_department is None:
        raise _field_error("invalid_reference", "dept_id", DEPARTMENT_NOT_FOUND_MESSAGE)
    company_id = current_department.company_id

    if "dept_id" in data:
        _validate_department(session, company_id=company_id, dept_id=data["dept_id"])
    if "position_id" in data:
        _validate_position(
            session, company_id=company_id, position_id=data["position_id"]
        )
    if data.get("cost_org_id") is not None:
        _validate_cost_center(
            session, company_id=company_id, cost_org_id=data["cost_org_id"]
        )
    if data.get("manager_id") is not None:
        _validate_manager(
            session,
            company_id=company_id,
            manager_id=data["manager_id"],
            employee_id=employee.id,
        )

    for field, value in data.items():
        setattr(employee, field, value)
    employee.updated_at = get_datetime_utc()

    session.add(employee)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_no_error()
    session.refresh(employee)
    return _public_one(session, employee)
