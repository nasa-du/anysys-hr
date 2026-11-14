"""Schedule-plan reads shared by the workbench and the rules page.

This slice only exposes the list needed by plan-level rule overrides; the
schedule-plan write path and expansion land with the A3 slice. Display names
are resolved with batched queries so a list never becomes N+1.
"""

import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select

from app.enums import PlanStatus, ScheduleScopeType
from app.models import (
    Department,
    Employee,
    PlanScope,
    Position,
    SchedulePlan,
)
from app.schemas_attendance.scheduling import (
    PlanScopePublic,
    SchedulePlanPublic,
    SchedulePlansPublic,
)
from app.services.common import paginate
from app.services.companies import get_company_or_404


def _month_start(month: str) -> date:
    return date(int(month[:4]), int(month[5:7]), 1)


def _scopes_by_plan(
    session: Session, plan_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[PlanScope]]:
    result: dict[uuid.UUID, list[PlanScope]] = defaultdict(list)
    if not plan_ids:
        return result
    scopes = session.exec(
        select(PlanScope).where(col(PlanScope.plan_id).in_(plan_ids))
    ).all()
    for scope in scopes:
        result[scope.plan_id].append(scope)
    return result


def _scope_labels(
    session: Session, scopes: list[PlanScope], scope_type: ScheduleScopeType
) -> dict[uuid.UUID, tuple[str, str]]:
    ids = {scope.scope_id for scope in scopes}
    if not ids:
        return {}

    if scope_type == ScheduleScopeType.DEPT:
        rows = session.exec(
            select(Department.id, Department.dept_code, Department.dept_name).where(
                col(Department.id).in_(ids)
            )
        ).all()
    elif scope_type == ScheduleScopeType.POSITION:
        rows = session.exec(
            select(Position.id, Position.position_code, Position.position_name).where(
                col(Position.id).in_(ids)
            )
        ).all()
    elif scope_type == ScheduleScopeType.EMPLOYEE:
        rows = session.exec(
            select(Employee.id, Employee.employee_no, Employee.name).where(
                col(Employee.id).in_(ids)
            )
        ).all()
    else:
        rows = []
    return {row[0]: (row[1], row[2]) for row in rows}


def _scope_publics(
    session: Session,
    plans: list[SchedulePlan],
    scopes_by_plan: dict[uuid.UUID, list[PlanScope]],
) -> dict[uuid.UUID, list[PlanScopePublic]]:
    labels_by_type: dict[ScheduleScopeType, dict[uuid.UUID, tuple[str, str]]] = {}
    for scope_type in (
        ScheduleScopeType.DEPT,
        ScheduleScopeType.POSITION,
        ScheduleScopeType.EMPLOYEE,
    ):
        scopes = [
            scope
            for plan in plans
            if plan.scope_type == scope_type
            for scope in scopes_by_plan.get(plan.id, [])
        ]
        labels_by_type[scope_type] = _scope_labels(session, scopes, scope_type)

    result: dict[uuid.UUID, list[PlanScopePublic]] = defaultdict(list)
    for plan in plans:
        labels = labels_by_type.get(plan.scope_type, {})
        for scope in scopes_by_plan.get(plan.id, []):
            code, name = labels.get(scope.scope_id, (None, None))
            result[plan.id].append(
                PlanScopePublic(
                    id=scope.id,
                    scope_id=scope.scope_id,
                    scope_code=code,
                    scope_name=name,
                )
            )
    return result


def list_schedule_plans(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str | None,
    status: PlanStatus | None,
    scope_type: ScheduleScopeType | None,
    keyword: str | None,
    skip: int,
    limit: int,
) -> SchedulePlansPublic:
    """List plans for one company ordered by month, name, and id."""
    get_company_or_404(session, company_id)

    filters: list[ColumnElement[bool]] = [col(SchedulePlan.company_id) == company_id]
    if month is not None:
        filters.append(col(SchedulePlan.month) == _month_start(month))
    if status is not None:
        filters.append(col(SchedulePlan.status) == status)
    if scope_type is not None:
        filters.append(col(SchedulePlan.scope_type) == scope_type)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        filters.append(col(SchedulePlan.plan_name).ilike(f"%{normalized_keyword}%"))

    statement = (
        select(SchedulePlan)
        .where(*filters)
        .order_by(
            col(SchedulePlan.month).desc(),
            col(SchedulePlan.plan_name).asc(),
            col(SchedulePlan.id).asc(),
        )
    )
    count_statement = select(func.count()).select_from(SchedulePlan).where(*filters)
    plans, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    plan_ids = [plan.id for plan in plans]

    scopes = _scopes_by_plan(session, plan_ids)
    scope_publics = _scope_publics(session, plans, scopes)

    return SchedulePlansPublic(
        data=[
            SchedulePlanPublic(
                id=plan.id,
                company_id=plan.company_id,
                month=plan.month.strftime("%Y-%m"),
                plan_name=plan.plan_name,
                scope_type=plan.scope_type,
                status=plan.status,
                copied_from_plan_id=plan.copied_from_plan_id,
                note=plan.note,
                scopes=scope_publics.get(plan.id, []),
                created_at=plan.created_at,
                updated_at=plan.updated_at,
            )
            for plan in plans
        ],
        count=count,
    )
