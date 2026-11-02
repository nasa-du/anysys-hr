"""Position business rules: CRUD, default departments, filtering, and blockers."""

import uuid

from sqlalchemy import ColumnElement, func, or_
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
    PositionCreate,
    PositionPublic,
    PositionsPublic,
    PositionUpdate,
)
from app.services.common import (
    ACTIVE_EMPLOYEE_STATUSES,
    BlockerQuery,
    collect_blockers,
    paginate,
)
from app.services.companies import get_company_or_404

COMPANY_NOT_FOUND_MESSAGE = "公司不存在"
POSITION_NOT_FOUND_MESSAGE = "岗位不存在"
DEPARTMENT_NOT_FOUND_MESSAGE = "部门不存在"
DEFAULT_DEPARTMENT_NOT_FOUND_MESSAGE = "默认部门不存在"
DUPLICATE_CODE_MESSAGE = "岗位编码已存在"
INACTIVE_ENTITY_MESSAGE = "岗位已停用，无法修改默认部门"
ACTIVATION_BLOCKED_MESSAGE = "公司已停用，无法启用"


def _duplicate_code_error() -> DomainError:
    return DomainError(
        "duplicate_code",
        DUPLICATE_CODE_MESSAGE,
        field_errors={"position_code": DUPLICATE_CODE_MESSAGE},
    )


def _field_error(code: str, field: str, message: str) -> DomainError:
    return DomainError(code, message, field_errors={field: message})


def get_position_or_404(session: Session, position_id: uuid.UUID) -> Position:
    position = session.get(Position, position_id)
    if position is None:
        raise DomainError("not_found", POSITION_NOT_FOUND_MESSAGE)
    return position


def _to_public(
    position: Position,
    companies: dict[uuid.UUID, Company],
    departments: dict[uuid.UUID, Department],
) -> PositionPublic:
    department = departments.get(position.dept_id) if position.dept_id else None
    return PositionPublic(
        id=position.id,
        position_code=position.position_code,
        position_name=position.position_name,
        company_id=position.company_id,
        dept_id=position.dept_id,
        order_no=position.order_no,
        is_active=position.is_active,
        note=position.note,
        created_at=position.created_at,
        updated_at=position.updated_at,
        company_name=companies[position.company_id].company_name,
        dept_name=department.dept_name if department else None,
    )


def _public_many(session: Session, positions: list[Position]) -> list[PositionPublic]:
    if not positions:
        return []

    company_ids = {position.company_id for position in positions}
    dept_ids = {
        position.dept_id for position in positions if position.dept_id is not None
    }

    companies = {
        company.id: company
        for company in session.exec(
            select(Company).where(col(Company.id).in_(company_ids))
        ).all()
    }
    departments = {
        department.id: department
        for department in session.exec(
            select(Department).where(col(Department.id).in_(dept_ids))
        ).all()
    }
    return [_to_public(position, companies, departments) for position in positions]


def _public_one(session: Session, position: Position) -> PositionPublic:
    return _public_many(session, [position])[0]


def get_position(session: Session, position_id: uuid.UUID) -> PositionPublic:
    """Return one position with its display fields resolved."""
    return _public_one(session, get_position_or_404(session, position_id))


def list_positions(
    session: Session,
    *,
    company_id: uuid.UUID,
    dept_id: uuid.UUID | None,
    keyword: str | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> PositionsPublic:
    get_company_or_404(session, company_id)
    if dept_id is not None and session.get(Department, dept_id) is None:
        raise DomainError("not_found", DEPARTMENT_NOT_FOUND_MESSAGE)

    filters: list[ColumnElement[bool]] = [col(Position.company_id) == company_id]
    if dept_id is not None:
        filters.append(col(Position.dept_id) == dept_id)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        filters.append(
            or_(
                col(Position.position_code).ilike(pattern),
                col(Position.position_name).ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(col(Position.is_active) == is_active)

    statement = (
        select(Position)
        .where(*filters)
        .order_by(col(Position.order_no).asc(), col(Position.position_code).asc())
    )
    count_statement = select(func.count()).select_from(Position).where(*filters)
    items, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return PositionsPublic(data=_public_many(session, items), count=count)


def _validate_default_department(
    session: Session, *, company_id: uuid.UUID, dept_id: uuid.UUID
) -> None:
    department = session.get(Department, dept_id)
    if department is None:
        raise _field_error(
            "invalid_reference", "dept_id", DEFAULT_DEPARTMENT_NOT_FOUND_MESSAGE
        )
    if department.company_id != company_id:
        raise _field_error("cross_company", "dept_id", "默认部门必须属于同一公司")
    if not department.is_active:
        raise _field_error("inactive_reference", "dept_id", "默认部门已停用")


def _validate_activation(session: Session, *, company_id: uuid.UUID) -> None:
    company = session.get(Company, company_id)
    if company is None or not company.is_active:
        raise DomainError(
            "activation_blocked",
            ACTIVATION_BLOCKED_MESSAGE,
            field_errors={"is_active": ACTIVATION_BLOCKED_MESSAGE},
        )


def create_position(session: Session, payload: PositionCreate) -> PositionPublic:
    company = session.get(Company, payload.company_id)
    if company is None:
        raise _field_error("invalid_reference", "company_id", COMPANY_NOT_FOUND_MESSAGE)
    if not company.is_active:
        raise _field_error(
            "inactive_reference", "company_id", "公司已停用，无法创建岗位"
        )

    existing = session.exec(
        select(Position).where(
            Position.company_id == company.id,
            Position.position_code == payload.position_code,
        )
    ).first()
    if existing is not None:
        raise _duplicate_code_error()

    if payload.dept_id is not None:
        _validate_default_department(
            session, company_id=company.id, dept_id=payload.dept_id
        )

    position = Position(
        position_code=payload.position_code,
        position_name=payload.position_name,
        company_id=company.id,
        dept_id=payload.dept_id,
        order_no=payload.order_no,
        is_active=payload.is_active,
        note=payload.note,
    )
    session.add(position)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_code_error()
    session.refresh(position)
    return _public_one(session, position)


def _position_blocker_queries(
    position_id: uuid.UUID, *, active_only: bool
) -> list[BlockerQuery]:
    """Employees that reference this position.

    ``active_only`` implements deactivation: active/probation employees block
    while resigned employees do not. Delete uses every reference, including
    resigned employees.
    """
    employee_conditions: list[ColumnElement[bool]] = [
        col(Employee.position_id) == position_id
    ]
    if active_only:
        employee_conditions.append(col(Employee.status).in_(ACTIVE_EMPLOYEE_STATUSES))

    return [
        BlockerQuery(
            type="employee",
            count_statement=select(func.count())
            .select_from(Employee)
            .where(*employee_conditions),
            rows_statement=select(Employee.id, Employee.employee_no, Employee.name)
            .where(*employee_conditions)
            .order_by(col(Employee.employee_no).asc()),
        )
    ]


def _blocker_counts(
    session: Session, queries: list[BlockerQuery]
) -> dict[BlockerType, int]:
    return {query.type: session.exec(query.count_statement).one() for query in queries}


def _delete_message(counts: dict[BlockerType, int]) -> str:
    return f"无法删除：仍有 {counts.get('employee', 0)} 名员工引用"


def _deactivate_message(counts: dict[BlockerType, int]) -> str:
    return f"无法停用：仍有 {counts.get('employee', 0)} 名在职/试用期员工引用"


def _referenced_error(session: Session, position_id: uuid.UUID) -> DomainError:
    queries = _position_blocker_queries(position_id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    return DomainError(
        "referenced",
        _delete_message(_blocker_counts(session, queries)),
        blockers=blockers,
        blocker_count=total,
    )


def update_position(
    session: Session, position_id: uuid.UUID, payload: PositionUpdate
) -> PositionPublic:
    position = get_position_or_404(session, position_id)
    data = payload.model_dump(exclude_unset=True)
    final_is_active = data.get("is_active", position.is_active)

    if data.get("is_active") is False and position.is_active:
        queries = _position_blocker_queries(position.id, active_only=True)
        total, blockers = collect_blockers(session, queries)
        if total:
            raise DomainError(
                "deactivate_blocked",
                _deactivate_message(_blocker_counts(session, queries)),
                field_errors={"is_active": "存在在职/试用期员工"},
                blockers=blockers,
                blocker_count=total,
            )

    if data.get("is_active") is True and not position.is_active:
        _validate_activation(session, company_id=position.company_id)

    if "dept_id" in data:
        if not final_is_active:
            raise _field_error("inactive_entity", "dept_id", INACTIVE_ENTITY_MESSAGE)
        dept_id = data["dept_id"]
        if dept_id is not None:
            _validate_default_department(
                session, company_id=position.company_id, dept_id=dept_id
            )

    for field, value in data.items():
        setattr(position, field, value)
    position.updated_at = get_datetime_utc()

    session.add(position)
    session.commit()
    session.refresh(position)
    return _public_one(session, position)


def delete_position(session: Session, position_id: uuid.UUID) -> Message:
    position = get_position_or_404(session, position_id)
    queries = _position_blocker_queries(position.id, active_only=False)
    total, blockers = collect_blockers(session, queries)
    if total:
        raise DomainError(
            "referenced",
            _delete_message(_blocker_counts(session, queries)),
            blockers=blockers,
            blocker_count=total,
        )

    session.delete(position)
    try:
        session.commit()
    except IntegrityError:
        # A reference appeared between the check and the delete; report the
        # current blockers rather than a bare conflict.
        session.rollback()
        raise _referenced_error(session, position_id)
    return Message(message="岗位删除成功")
