"""Department business rules: CRUD, tree reads, hierarchy, and blockers."""

import uuid

from sqlalchemy import ColumnElement, func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import BlockerType, DomainError
from app.models import (
    Company,
    Department,
    Employee,
    Message,
    Position,
    get_datetime_utc,
)
from app.schemas_basic import (
    DepartmentCreate,
    DepartmentPublic,
    DepartmentsPublic,
    DepartmentTreeNode,
    DepartmentTreePublic,
    DepartmentUpdate,
)
from app.services.common import (
    ACTIVE_EMPLOYEE_STATUSES,
    BlockerQuery,
    collect_blockers,
    paginate,
)
from app.services.companies import get_company_or_404

COMPANY_NOT_FOUND_MESSAGE = "公司不存在"
DEPARTMENT_NOT_FOUND_MESSAGE = "部门不存在"
PARENT_NOT_FOUND_MESSAGE = "上级部门不存在"
MANAGER_NOT_FOUND_MESSAGE = "直属上级不存在"
DUPLICATE_CODE_MESSAGE = "部门编码已存在"
CYCLE_MESSAGE = "上级部门不能是自身或下级部门"
INACTIVE_ENTITY_MESSAGE = "部门已停用，无法修改上级部门"
ACTIVATION_BLOCKED_MESSAGE = "公司或上级部门已停用，无法启用"


def _duplicate_code_error() -> DomainError:
    return DomainError(
        "duplicate_code",
        DUPLICATE_CODE_MESSAGE,
        field_errors={"dept_code": DUPLICATE_CODE_MESSAGE},
    )


def _field_error(code: str, field: str, message: str) -> DomainError:
    return DomainError(code, message, field_errors={field: message})


def get_department_or_404(session: Session, department_id: uuid.UUID) -> Department:
    department = session.get(Department, department_id)
    if department is None:
        raise DomainError("not_found", DEPARTMENT_NOT_FOUND_MESSAGE)
    return department


def _to_public(
    department: Department,
    companies: dict[uuid.UUID, Company],
    parents: dict[uuid.UUID, Department],
    managers: dict[uuid.UUID, Employee],
) -> DepartmentPublic:
    parent = parents.get(department.parent_id) if department.parent_id else None
    manager = managers.get(department.manager_id) if department.manager_id else None
    return DepartmentPublic(
        id=department.id,
        dept_code=department.dept_code,
        dept_name=department.dept_name,
        company_id=department.company_id,
        parent_id=department.parent_id,
        manager_id=department.manager_id,
        order_no=department.order_no,
        is_active=department.is_active,
        note=department.note,
        created_at=department.created_at,
        updated_at=department.updated_at,
        company_name=companies[department.company_id].company_name,
        parent_name=parent.dept_name if parent else None,
        manager_name=manager.name if manager else None,
        manager_status=manager.status if manager else None,
    )


def _public_many(
    session: Session, departments: list[Department]
) -> list[DepartmentPublic]:
    if not departments:
        return []

    company_ids = {department.company_id for department in departments}
    parent_ids = {d.parent_id for d in departments if d.parent_id is not None}
    manager_ids = {d.manager_id for d in departments if d.manager_id is not None}

    companies = {
        company.id: company
        for company in session.exec(
            select(Company).where(col(Company.id).in_(company_ids))
        ).all()
    }
    parents = {
        parent.id: parent
        for parent in session.exec(
            select(Department).where(col(Department.id).in_(parent_ids))
        ).all()
    }
    managers = {
        manager.id: manager
        for manager in session.exec(
            select(Employee).where(col(Employee.id).in_(manager_ids))
        ).all()
    }
    return [
        _to_public(department, companies, parents, managers)
        for department in departments
    ]


def _public_one(session: Session, department: Department) -> DepartmentPublic:
    return _public_many(session, [department])[0]


def get_department(session: Session, department_id: uuid.UUID) -> DepartmentPublic:
    """Return one department with its display fields resolved."""
    return _public_one(session, get_department_or_404(session, department_id))


def list_departments(
    session: Session,
    *,
    company_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    keyword: str | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> DepartmentsPublic:
    get_company_or_404(session, company_id)
    if parent_id is not None and session.get(Department, parent_id) is None:
        raise DomainError("not_found", PARENT_NOT_FOUND_MESSAGE)

    filters: list[ColumnElement[bool]] = [col(Department.company_id) == company_id]
    if parent_id is not None:
        filters.append(col(Department.parent_id) == parent_id)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        filters.append(
            or_(
                col(Department.dept_code).ilike(pattern),
                col(Department.dept_name).ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(col(Department.is_active) == is_active)

    statement = (
        select(Department)
        .where(*filters)
        .order_by(col(Department.order_no).asc(), col(Department.dept_code).asc())
    )
    count_statement = select(func.count()).select_from(Department).where(*filters)
    items, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return DepartmentsPublic(data=_public_many(session, items), count=count)


def _build_tree(
    session: Session, departments: list[Department]
) -> list[DepartmentTreeNode]:
    nodes = {
        public.id: DepartmentTreeNode(**public.model_dump(), children=[])
        for public in _public_many(session, departments)
    }
    roots: list[DepartmentTreeNode] = []
    for department in departments:
        node = nodes[department.id]
        parent_id = department.parent_id
        parent = nodes.get(parent_id) if parent_id is not None else None
        if parent is None:
            roots.append(node)
        else:
            parent.children.append(node)
    return roots


def tree_departments(
    session: Session, *, company_id: uuid.UUID, is_active: bool | None
) -> DepartmentTreePublic:
    get_company_or_404(session, company_id)
    statement = select(Department).where(col(Department.company_id) == company_id)
    if is_active is not None:
        statement = statement.where(col(Department.is_active) == is_active)
    statement = statement.order_by(
        col(Department.order_no).asc(), col(Department.dept_code).asc()
    )
    departments = list(session.exec(statement).all())
    return DepartmentTreePublic(data=_build_tree(session, departments))


def _creates_cycle(
    session: Session, department_id: uuid.UUID, parent: Department
) -> bool:
    """Walk up from the candidate parent; hitting the node closes a cycle."""
    current: Department | None = parent
    seen: set[uuid.UUID] = set()
    while current is not None:
        if current.id == department_id or current.id in seen:
            return True
        seen.add(current.id)
        current = (
            session.get(Department, current.parent_id) if current.parent_id else None
        )
    return False


def _validate_parent(
    session: Session,
    *,
    company_id: uuid.UUID,
    department_id: uuid.UUID | None,
    parent_id: uuid.UUID,
) -> None:
    parent = session.get(Department, parent_id)
    if parent is None:
        raise _field_error("invalid_reference", "parent_id", PARENT_NOT_FOUND_MESSAGE)
    if parent.company_id != company_id:
        raise _field_error("cross_company", "parent_id", "上级部门必须属于同一公司")
    if department_id is not None and _creates_cycle(session, department_id, parent):
        raise _field_error("cycle", "parent_id", CYCLE_MESSAGE)
    if not parent.is_active:
        raise _field_error("inactive_reference", "parent_id", "上级部门已停用")


def _validate_manager(
    session: Session, *, company_id: uuid.UUID, manager_id: uuid.UUID
) -> None:
    manager = session.get(Employee, manager_id)
    if manager is None:
        raise _field_error("invalid_reference", "manager_id", MANAGER_NOT_FOUND_MESSAGE)
    manager_department = session.get(Department, manager.dept_id)
    if manager_department is None or manager_department.company_id != company_id:
        raise _field_error("cross_company", "manager_id", "直属上级必须属于同一公司")
    if manager.status not in ACTIVE_EMPLOYEE_STATUSES:
        raise _field_error(
            "inactive_reference", "manager_id", "直属上级必须是在职或试用期员工"
        )


def _validate_activation(
    session: Session, *, company_id: uuid.UUID, parent_id: uuid.UUID | None
) -> None:
    message = ACTIVATION_BLOCKED_MESSAGE
    company = session.get(Company, company_id)
    if company is None or not company.is_active:
        raise DomainError(
            "activation_blocked", message, field_errors={"is_active": message}
        )

    current = session.get(Department, parent_id) if parent_id is not None else None
    seen: set[uuid.UUID] = set()
    while current is not None:
        if not current.is_active:
            raise DomainError(
                "activation_blocked", message, field_errors={"is_active": message}
            )
        if current.id in seen:
            break
        seen.add(current.id)
        current = (
            session.get(Department, current.parent_id) if current.parent_id else None
        )


def create_department(session: Session, payload: DepartmentCreate) -> DepartmentPublic:
    company = session.get(Company, payload.company_id)
    if company is None:
        raise _field_error("invalid_reference", "company_id", COMPANY_NOT_FOUND_MESSAGE)
    if not company.is_active:
        raise _field_error(
            "inactive_reference", "company_id", "公司已停用，无法创建部门"
        )

    existing = session.exec(
        select(Department).where(
            Department.company_id == company.id,
            Department.dept_code == payload.dept_code,
        )
    ).first()
    if existing is not None:
        raise _duplicate_code_error()

    if payload.parent_id is not None:
        _validate_parent(
            session,
            company_id=company.id,
            department_id=None,
            parent_id=payload.parent_id,
        )
    if payload.manager_id is not None:
        _validate_manager(session, company_id=company.id, manager_id=payload.manager_id)

    department = Department(
        dept_code=payload.dept_code,
        dept_name=payload.dept_name,
        company_id=company.id,
        parent_id=payload.parent_id,
        manager_id=payload.manager_id,
        order_no=payload.order_no,
        is_active=payload.is_active,
        note=payload.note,
    )
    session.add(department)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_code_error()
    session.refresh(department)
    return _public_one(session, department)


def _department_blocker_queries(
    department_id: uuid.UUID, *, active_only: bool
) -> list[BlockerQuery]:
    """Child departments and employees that reference this department.

    ``active_only`` implements deactivation: active child departments and
    active/probation employees block; resigned employees do not. Delete uses
    every reference, including inactive children and resigned employees.
    """
    child_conditions: list[ColumnElement[bool]] = [
        col(Department.parent_id) == department_id
    ]
    employee_conditions: list[ColumnElement[bool]] = [
        col(Employee.dept_id) == department_id
    ]
    if active_only:
        child_conditions.append(col(Department.is_active).is_(True))
        employee_conditions.append(col(Employee.status).in_(ACTIVE_EMPLOYEE_STATUSES))

    return [
        BlockerQuery(
            type="department",
            count_statement=select(func.count())
            .select_from(Department)
            .where(*child_conditions),
            rows_statement=select(
                Department.id, Department.dept_code, Department.dept_name
            )
            .where(*child_conditions)
            .order_by(col(Department.dept_code).asc()),
        ),
        BlockerQuery(
            type="employee",
            count_statement=select(func.count())
            .select_from(Employee)
            .where(*employee_conditions),
            rows_statement=select(Employee.id, Employee.employee_no, Employee.name)
            .where(*employee_conditions)
            .order_by(col(Employee.employee_no).asc()),
        ),
    ]


def _blocker_counts(
    session: Session, queries: list[BlockerQuery]
) -> dict[BlockerType, int]:
    return {query.type: session.exec(query.count_statement).one() for query in queries}


def _delete_message(counts: dict[BlockerType, int]) -> str:
    parts = []
    if child_count := counts.get("department", 0):
        parts.append(f"{child_count} 个子部门")
    if employee_count := counts.get("employee", 0):
        parts.append(f"{employee_count} 名员工")
    return f"无法删除：仍有 {'、'.join(parts)}引用"


def _deactivate_message(counts: dict[BlockerType, int]) -> str:
    parts = []
    if child_count := counts.get("department", 0):
        parts.append(f"{child_count} 个启用中的下级部门")
    if employee_count := counts.get("employee", 0):
        parts.append(f"{employee_count} 名在职/试用期员工")
    return f"无法停用：仍有 {'、'.join(parts)}引用"


def _referenced_error(session: Session, department_id: uuid.UUID) -> DomainError:
    queries = _department_blocker_queries(department_id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    return DomainError(
        "referenced",
        _delete_message(_blocker_counts(session, queries)),
        blockers=blockers,
        blocker_count=total,
    )


def update_department(
    session: Session, department_id: uuid.UUID, payload: DepartmentUpdate
) -> DepartmentPublic:
    department = get_department_or_404(session, department_id)
    data = payload.model_dump(exclude_unset=True)
    final_is_active = data.get("is_active", department.is_active)

    if data.get("is_active") is False and department.is_active:
        queries = _department_blocker_queries(department.id, active_only=True)
        total, blockers = collect_blockers(session, queries)
        if total:
            raise DomainError(
                "deactivate_blocked",
                _deactivate_message(_blocker_counts(session, queries)),
                field_errors={"is_active": "存在启用中的下级部门或在职/试用期员工"},
                blockers=blockers,
                blocker_count=total,
            )

    if data.get("is_active") is True and not department.is_active:
        _validate_activation(
            session,
            company_id=department.company_id,
            parent_id=data.get("parent_id", department.parent_id),
        )

    if "parent_id" in data:
        if not final_is_active:
            raise _field_error("inactive_entity", "parent_id", INACTIVE_ENTITY_MESSAGE)
        parent_id = data["parent_id"]
        if parent_id is not None:
            _validate_parent(
                session,
                company_id=department.company_id,
                department_id=department.id,
                parent_id=parent_id,
            )

    manager_id = data.get("manager_id")
    if "manager_id" in data and manager_id is not None:
        _validate_manager(
            session, company_id=department.company_id, manager_id=manager_id
        )

    for field, value in data.items():
        setattr(department, field, value)
    department.updated_at = get_datetime_utc()

    session.add(department)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_code_error()
    session.refresh(department)
    return _public_one(session, department)


def delete_department(session: Session, department_id: uuid.UUID) -> Message:
    department = get_department_or_404(session, department_id)
    queries = _department_blocker_queries(department.id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    if total:
        raise DomainError(
            "referenced",
            _delete_message(_blocker_counts(session, queries)),
            blockers=blockers,
            blocker_count=total,
        )

    # The FK is ON DELETE SET NULL, but the contract asks the service to clear
    # the default department explicitly so the behavior does not rely on it.
    session.exec(
        update(Position)
        .where(col(Position.dept_id) == department.id)
        .values(dept_id=None, updated_at=get_datetime_utc())
    )
    session.delete(department)
    try:
        session.commit()
    except IntegrityError:
        # A reference appeared between the check and the delete; report the
        # current blockers rather than a bare conflict.
        session.rollback()
        raise _referenced_error(session, department_id)
    return Message(message="部门删除成功")
