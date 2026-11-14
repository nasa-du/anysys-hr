"""Company business rules: CRUD, filtering, and reference blocking."""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import Blocker, BlockerType, DomainError
from app.models import (
    Company,
    CostCenter,
    Department,
    Employee,
    Message,
    Position,
    get_datetime_utc,
)
from app.schemas_basic import (
    CompaniesPublic,
    CompanyCreate,
    CompanyPublic,
    CompanyUpdate,
)
from app.services.common import (
    ACTIVE_EMPLOYEE_STATUSES,
    BlockerQuery,
    collect_blockers,
    paginate,
)

NOT_FOUND_MESSAGE = "公司不存在"
DUPLICATE_CODE_MESSAGE = "公司编码已存在"


def _duplicate_code_error() -> DomainError:
    return DomainError(
        "duplicate_code",
        DUPLICATE_CODE_MESSAGE,
        field_errors={"company_code": DUPLICATE_CODE_MESSAGE},
    )


def get_company_or_404(session: Session, company_id: uuid.UUID) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise DomainError("not_found", NOT_FOUND_MESSAGE)
    return company


def list_companies(
    session: Session,
    *,
    skip: int,
    limit: int,
    keyword: str | None,
    is_active: bool | None,
) -> CompaniesPublic:
    statement = select(Company)
    count_statement = select(func.count()).select_from(Company)

    filters: list[ColumnElement[bool]] = []
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        pattern = f"%{normalized_keyword}%"
        filters.append(
            or_(
                col(Company.company_code).ilike(pattern),
                col(Company.company_name).ilike(pattern),
            )
        )
    if is_active is not None:
        filters.append(col(Company.is_active) == is_active)
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    statement = statement.order_by(col(Company.company_code).asc())
    items, count = paginate(session, statement, count_statement, skip=skip, limit=limit)

    return CompaniesPublic(
        data=[CompanyPublic.model_validate(company) for company in items],
        count=count,
    )


def create_company(session: Session, payload: CompanyCreate) -> CompanyPublic:
    code = payload.company_code
    existing = session.exec(select(Company).where(Company.company_code == code)).first()
    if existing is not None:
        raise _duplicate_code_error()

    company = Company(
        company_code=code,
        company_name=payload.company_name,
        is_active=payload.is_active,
        note=payload.note,
    )
    session.add(company)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _duplicate_code_error()
    session.refresh(company)
    return CompanyPublic.model_validate(company)


def _company_owned_query(
    *,
    type: BlockerType,
    model: Any,
    columns: tuple[Any, Any, Any],
    conditions: list[ColumnElement[bool]],
    code_column: Any,
) -> BlockerQuery:
    return BlockerQuery(
        type=type,
        count_statement=select(func.count()).select_from(model).where(*conditions),
        rows_statement=select(*columns)
        .where(*conditions)
        .order_by(col(code_column).asc()),
    )


def _organization_blocker_queries(
    company_id: uuid.UUID, *, active_only: bool
) -> list[BlockerQuery]:
    """Reference sources owned by a company.

    ``active_only`` implements the deactivation rule: active children and
    active/probation employees block; resigned employees do not. Delete uses
    every reference, including inactive and resigned rows.
    """
    department_conditions: list[ColumnElement[bool]] = [
        col(Department.company_id) == company_id
    ]
    position_conditions: list[ColumnElement[bool]] = [
        col(Position.company_id) == company_id
    ]
    cost_center_conditions: list[ColumnElement[bool]] = [
        col(CostCenter.company_id) == company_id
    ]
    employee_conditions: list[ColumnElement[bool]] = [
        col(Department.company_id) == company_id,
    ]
    if active_only:
        department_conditions.append(col(Department.is_active).is_(True))
        position_conditions.append(col(Position.is_active).is_(True))
        cost_center_conditions.append(col(CostCenter.is_active).is_(True))
        employee_conditions.append(col(Employee.status).in_(ACTIVE_EMPLOYEE_STATUSES))

    employee_query = BlockerQuery(
        type="employee",
        count_statement=select(func.count())
        .select_from(Employee)
        .join(Department, col(Employee.dept_id) == col(Department.id))
        .where(*employee_conditions),
        rows_statement=select(Employee.id, Employee.employee_no, Employee.name)
        .join(Department, col(Employee.dept_id) == col(Department.id))
        .where(*employee_conditions)
        .order_by(col(Employee.employee_no).asc()),
    )

    return [
        _company_owned_query(
            type="department",
            model=Department,
            columns=(Department.id, Department.dept_code, Department.dept_name),
            conditions=department_conditions,
            code_column=Department.dept_code,
        ),
        _company_owned_query(
            type="position",
            model=Position,
            columns=(
                Position.id,
                Position.position_code,
                Position.position_name,
            ),
            conditions=position_conditions,
            code_column=Position.position_code,
        ),
        _company_owned_query(
            type="cost_center",
            model=CostCenter,
            columns=(
                CostCenter.id,
                CostCenter.cost_org_code,
                CostCenter.cost_org_name,
            ),
            conditions=cost_center_conditions,
            code_column=CostCenter.cost_org_code,
        ),
        employee_query,
    ]


def _company_blockers(
    session: Session, company_id: uuid.UUID, *, active_only: bool
) -> tuple[int, list[Blocker]]:
    return collect_blockers(
        session, _organization_blocker_queries(company_id, active_only=active_only)
    )


def update_company(
    session: Session, company_id: uuid.UUID, payload: CompanyUpdate
) -> CompanyPublic:
    company = get_company_or_404(session, company_id)
    data = payload.model_dump(exclude_unset=True)

    if data.get("is_active") is False and company.is_active:
        count, blockers = _company_blockers(session, company.id, active_only=True)
        if count:
            raise DomainError(
                "deactivate_blocked",
                f"无法停用：仍有 {count} 个启用中的下级部门、岗位、成本中心"
                "或在职/试用期员工引用",
                field_errors={
                    "is_active": "存在启用中的下级部门、岗位、成本中心或在职/试用期员工"
                },
                blockers=blockers,
                blocker_count=count,
            )

    for field, value in data.items():
        setattr(company, field, value)
    company.updated_at = get_datetime_utc()

    session.add(company)
    session.commit()
    session.refresh(company)
    return CompanyPublic.model_validate(company)


def delete_company(session: Session, company_id: uuid.UUID) -> Message:
    company = get_company_or_404(session, company_id)
    count, blockers = _company_blockers(session, company.id, active_only=False)
    if count:
        raise DomainError(
            "referenced",
            f"无法删除：仍有 {count} 个部门、岗位、成本中心或员工引用",
            blockers=blockers,
            blocker_count=count,
        )

    session.delete(company)
    try:
        session.commit()
    except IntegrityError:
        # A reference appeared between the check and the delete; report the
        # current Basic Management blockers rather than database text. A
        # company referenced solely by attendance rows has no Basic Management
        # blocker to enumerate, so return a clear generic conflict.
        session.rollback()
        count, blockers = _company_blockers(session, company.id, active_only=False)
        if count:
            raise DomainError(
                "referenced",
                f"无法删除：仍有 {count} 个部门、岗位、成本中心或员工引用",
                blockers=blockers,
                blocker_count=count,
            )
        raise DomainError("referenced", "无法删除：公司仍被考勤数据引用")
    return Message(message="公司删除成功")
