"""Cost center business rules: CRUD, tree reads, hierarchy, and blockers."""

import uuid

from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import BlockerType, DomainError
from app.models import (
    Company,
    CostCenter,
    Department,
    Employee,
    Message,
    get_datetime_utc,
)
from app.schemas_basic import (
    CostCenterCreate,
    CostCenterPublic,
    CostCentersPublic,
    CostCenterTreeNode,
    CostCenterTreePublic,
    CostCenterUpdate,
)
from app.services.common import (
    ACTIVE_EMPLOYEE_STATUSES,
    BlockerQuery,
    collect_blockers,
    paginate,
)
from app.services.companies import get_company_or_404

COMPANY_NOT_FOUND_MESSAGE = "公司不存在"
COST_CENTER_NOT_FOUND_MESSAGE = "成本中心不存在"
PARENT_NOT_FOUND_MESSAGE = "上级成本中心不存在"
MANAGER_NOT_FOUND_MESSAGE = "直属上级不存在"
DUPLICATE_CODE_MESSAGE = "成本中心编码已存在"
CYCLE_MESSAGE = "上级成本中心不能是自身或下级成本中心"
INACTIVE_ENTITY_MESSAGE = "成本中心已停用，无法修改上级成本中心"
ACTIVATION_BLOCKED_MESSAGE = "公司或上级成本中心已停用，无法启用"


def _duplicate_code_error() -> DomainError:
    return DomainError(
        "duplicate_code",
        DUPLICATE_CODE_MESSAGE,
        field_errors={"cost_org_code": DUPLICATE_CODE_MESSAGE},
    )


def _field_error(code: str, field: str, message: str) -> DomainError:
    return DomainError(code, message, field_errors={field: message})


def get_cost_center_or_404(session: Session, cost_center_id: uuid.UUID) -> CostCenter:
    cost_center = session.get(CostCenter, cost_center_id)
    if cost_center is None:
        raise DomainError("not_found", COST_CENTER_NOT_FOUND_MESSAGE)
    return cost_center


def _to_public(
    cost_center: CostCenter,
    companies: dict[uuid.UUID, Company],
    parents: dict[uuid.UUID, CostCenter],
    managers: dict[uuid.UUID, Employee],
) -> CostCenterPublic:
    parent = parents.get(cost_center.parent_id) if cost_center.parent_id else None
    manager = managers.get(cost_center.manager_id) if cost_center.manager_id else None
    return CostCenterPublic(
        id=cost_center.id,
        cost_org_code=cost_center.cost_org_code,
        cost_org_name=cost_center.cost_org_name,
        company_id=cost_center.company_id,
        parent_id=cost_center.parent_id,
        manager_id=cost_center.manager_id,
        budget=cost_center.budget,
        warn_pct=cost_center.warn_pct,
        order_no=cost_center.order_no,
        is_active=cost_center.is_active,
        note=cost_center.note,
        created_at=cost_center.created_at,
        updated_at=cost_center.updated_at,
        company_name=companies[cost_center.company_id].company_name,
        parent_name=parent.cost_org_name if parent else None,
        manager_name=manager.name if manager else None,
        manager_status=manager.status if manager else None,
    )


def _public_many(
    session: Session, cost_centers: list[CostCenter]
) -> list[CostCenterPublic]:
    if not cost_centers:
        return []

    company_ids = {cost_center.company_id for cost_center in cost_centers}
    parent_ids = {
        cost_center.parent_id
        for cost_center in cost_centers
        if cost_center.parent_id is not None
    }
    manager_ids = {
        cost_center.manager_id
        for cost_center in cost_centers
        if cost_center.manager_id is not None
    }

    companies = {
        company.id: company
        for company in session.exec(
            select(Company).where(col(Company.id).in_(company_ids))
        ).all()
    }
    parents = {
        parent.id: parent
        for parent in session.exec(
            select(CostCenter).where(col(CostCenter.id).in_(parent_ids))
        ).all()
    }
    managers = {
        manager.id: manager
        for manager in session.exec(
            select(Employee).where(col(Employee.id).in_(manager_ids))
        ).all()
    }
    return [
        _to_public(cost_center, companies, parents, managers)
        for cost_center in cost_centers
    ]


def _public_one(session: Session, cost_center: CostCenter) -> CostCenterPublic:
    return _public_many(session, [cost_center])[0]


def get_cost_center(session: Session, cost_center_id: uuid.UUID) -> CostCenterPublic:
    """Return one cost center with its display fields resolved."""
    return _public_one(session, get_cost_center_or_404(session, cost_center_id))


def list_cost_centers(
    session: Session,
    *,
    company_id: uuid.UUID,
    parent_id: uuid.UUID | None,
    keyword: str | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> CostCentersPublic:
    get_company_or_404(session, company_id)
    if parent_id is not None and session.get(CostCenter, parent_id) is None:
        raise DomainError("not_found", PARENT_NOT_FOUND_MESSAGE)

    filters: list[ColumnElement[bool]] = [col(CostCenter.company_id) == company_id]
    if parent_id is not None:
        filters.append(col(CostCenter.parent_id) == parent_id)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        filters.append(
            or_(
                col(CostCenter.cost_org_code).ilike(pattern),
                col(CostCenter.cost_org_name).ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(col(CostCenter.is_active) == is_active)

    statement = (
        select(CostCenter)
        .where(*filters)
        .order_by(col(CostCenter.order_no).asc(), col(CostCenter.cost_org_code).asc())
    )
    count_statement = select(func.count()).select_from(CostCenter).where(*filters)
    items, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return CostCentersPublic(data=_public_many(session, items), count=count)


def _build_tree(
    session: Session, cost_centers: list[CostCenter]
) -> list[CostCenterTreeNode]:
    nodes = {
        public.id: CostCenterTreeNode(**public.model_dump(), children=[])
        for public in _public_many(session, cost_centers)
    }
    roots: list[CostCenterTreeNode] = []
    for cost_center in cost_centers:
        node = nodes[cost_center.id]
        parent_id = cost_center.parent_id
        parent = nodes.get(parent_id) if parent_id is not None else None
        if parent is None:
            roots.append(node)
        else:
            parent.children.append(node)
    return roots


def tree_cost_centers(
    session: Session, *, company_id: uuid.UUID, is_active: bool | None
) -> CostCenterTreePublic:
    get_company_or_404(session, company_id)
    statement = select(CostCenter).where(col(CostCenter.company_id) == company_id)
    if is_active is not None:
        statement = statement.where(col(CostCenter.is_active) == is_active)
    statement = statement.order_by(
        col(CostCenter.order_no).asc(), col(CostCenter.cost_org_code).asc()
    )
    cost_centers = list(session.exec(statement).all())
    return CostCenterTreePublic(data=_build_tree(session, cost_centers))


def _creates_cycle(
    session: Session, cost_center_id: uuid.UUID, parent: CostCenter
) -> bool:
    """Walk up from the candidate parent; hitting the node closes a cycle."""
    current: CostCenter | None = parent
    seen: set[uuid.UUID] = set()
    while current is not None:
        if current.id == cost_center_id or current.id in seen:
            return True
        seen.add(current.id)
        current = (
            session.get(CostCenter, current.parent_id) if current.parent_id else None
        )
    return False


def _validate_parent(
    session: Session,
    *,
    company_id: uuid.UUID,
    cost_center_id: uuid.UUID | None,
    parent_id: uuid.UUID,
) -> None:
    parent = session.get(CostCenter, parent_id)
    if parent is None:
        raise _field_error("invalid_reference", "parent_id", PARENT_NOT_FOUND_MESSAGE)
    if parent.company_id != company_id:
        raise _field_error("cross_company", "parent_id", "上级成本中心必须属于同一公司")
    if cost_center_id is not None and _creates_cycle(session, cost_center_id, parent):
        raise _field_error("cycle", "parent_id", CYCLE_MESSAGE)
    if not parent.is_active:
        raise _field_error("inactive_reference", "parent_id", "上级成本中心已停用")


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

    current = session.get(CostCenter, parent_id) if parent_id is not None else None
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
            session.get(CostCenter, current.parent_id) if current.parent_id else None
        )


def create_cost_center(session: Session, payload: CostCenterCreate) -> CostCenterPublic:
    company = session.get(Company, payload.company_id)
    if company is None:
        raise _field_error("invalid_reference", "company_id", COMPANY_NOT_FOUND_MESSAGE)
    if not company.is_active:
        raise _field_error(
            "inactive_reference", "company_id", "公司已停用，无法创建成本中心"
        )

    existing = session.exec(
        select(CostCenter).where(
            CostCenter.company_id == company.id,
            CostCenter.cost_org_code == payload.cost_org_code,
        )
    ).first()
    if existing is not None:
        raise _duplicate_code_error()

    if payload.parent_id is not None:
        _validate_parent(
            session,
            company_id=company.id,
            cost_center_id=None,
            parent_id=payload.parent_id,
        )
    if payload.manager_id is not None:
        _validate_manager(session, company_id=company.id, manager_id=payload.manager_id)

    cost_center = CostCenter(
        cost_org_code=payload.cost_org_code,
        cost_org_name=payload.cost_org_name,
        company_id=company.id,
        parent_id=payload.parent_id,
        manager_id=payload.manager_id,
        budget=payload.budget,
        warn_pct=payload.warn_pct,
        order_no=payload.order_no,
        is_active=payload.is_active,
        note=payload.note,
    )
    session.add(cost_center)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_code_error()
    session.refresh(cost_center)
    return _public_one(session, cost_center)


def _cost_center_blocker_queries(
    cost_center_id: uuid.UUID, *, active_only: bool
) -> list[BlockerQuery]:
    """Child cost centers and employees that reference this cost center.

    ``active_only`` implements deactivation: active child cost centers and
    active/probation employees block; resigned employees do not. Delete uses
    every reference, including inactive children and resigned employees.
    """
    child_conditions: list[ColumnElement[bool]] = [
        col(CostCenter.parent_id) == cost_center_id
    ]
    employee_conditions: list[ColumnElement[bool]] = [
        col(Employee.cost_org_id) == cost_center_id
    ]
    if active_only:
        child_conditions.append(col(CostCenter.is_active).is_(True))
        employee_conditions.append(col(Employee.status).in_(ACTIVE_EMPLOYEE_STATUSES))

    return [
        BlockerQuery(
            type="cost_center",
            count_statement=select(func.count())
            .select_from(CostCenter)
            .where(*child_conditions),
            rows_statement=select(
                CostCenter.id, CostCenter.cost_org_code, CostCenter.cost_org_name
            )
            .where(*child_conditions)
            .order_by(col(CostCenter.cost_org_code).asc()),
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
    if child_count := counts.get("cost_center", 0):
        parts.append(f"{child_count} 个下级成本中心")
    if employee_count := counts.get("employee", 0):
        parts.append(f"{employee_count} 名员工")
    return f"无法删除：仍有 {'、'.join(parts)}引用"


def _deactivate_message(counts: dict[BlockerType, int]) -> str:
    parts = []
    if child_count := counts.get("cost_center", 0):
        parts.append(f"{child_count} 个启用中的下级成本中心")
    if employee_count := counts.get("employee", 0):
        parts.append(f"{employee_count} 名在职/试用期员工")
    return f"无法停用：仍有 {'、'.join(parts)}引用"


def _referenced_error(session: Session, cost_center_id: uuid.UUID) -> DomainError:
    queries = _cost_center_blocker_queries(cost_center_id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    return DomainError(
        "referenced",
        _delete_message(_blocker_counts(session, queries)),
        blockers=blockers,
        blocker_count=total,
    )


def update_cost_center(
    session: Session, cost_center_id: uuid.UUID, payload: CostCenterUpdate
) -> CostCenterPublic:
    cost_center = get_cost_center_or_404(session, cost_center_id)
    data = payload.model_dump(exclude_unset=True)
    final_is_active = data.get("is_active", cost_center.is_active)

    if data.get("is_active") is False and cost_center.is_active:
        queries = _cost_center_blocker_queries(cost_center.id, active_only=True)
        total, blockers = collect_blockers(session, queries)
        if total:
            raise DomainError(
                "deactivate_blocked",
                _deactivate_message(_blocker_counts(session, queries)),
                field_errors={"is_active": "存在启用中的下级成本中心或在职/试用期员工"},
                blockers=blockers,
                blocker_count=total,
            )

    if data.get("is_active") is True and not cost_center.is_active:
        _validate_activation(
            session,
            company_id=cost_center.company_id,
            parent_id=data.get("parent_id", cost_center.parent_id),
        )

    if "parent_id" in data:
        if not final_is_active:
            raise _field_error("inactive_entity", "parent_id", INACTIVE_ENTITY_MESSAGE)
        parent_id = data["parent_id"]
        if parent_id is not None:
            _validate_parent(
                session,
                company_id=cost_center.company_id,
                cost_center_id=cost_center.id,
                parent_id=parent_id,
            )

    manager_id = data.get("manager_id")
    if "manager_id" in data and manager_id is not None:
        _validate_manager(
            session, company_id=cost_center.company_id, manager_id=manager_id
        )

    for field, value in data.items():
        setattr(cost_center, field, value)
    cost_center.updated_at = get_datetime_utc()

    session.add(cost_center)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_code_error()
    session.refresh(cost_center)
    return _public_one(session, cost_center)


def delete_cost_center(session: Session, cost_center_id: uuid.UUID) -> Message:
    cost_center = get_cost_center_or_404(session, cost_center_id)
    queries = _cost_center_blocker_queries(cost_center.id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    if total:
        raise DomainError(
            "referenced",
            _delete_message(_blocker_counts(session, queries)),
            blockers=blockers,
            blocker_count=total,
        )

    session.delete(cost_center)
    try:
        session.commit()
    except IntegrityError:
        # A reference appeared between the check and the delete; report the
        # current blockers rather than a bare conflict.
        session.rollback()
        raise _referenced_error(session, cost_center_id)
    return Message(message="成本中心删除成功")
