import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.enums import PlanStatus, ScheduleScopeType
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.scheduling import (
    PlanRuleOverridesPublic,
    PlanRuleOverridesUpdate,
    SchedulePlansPublic,
)
from app.services.attendance import rules as rule_service
from app.services.attendance import schedule_plans as plan_service

router = APIRouter(
    prefix="/attendance/schedule-plans",
    tags=["attendance-schedule-plans"],
    dependencies=[Depends(attendance_access)],
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
}

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=500)]
Keyword = Annotated[str | None, Query(max_length=100)]


@router.get("/", response_model=SchedulePlansPublic, responses=ERROR_RESPONSES)
def read_schedule_plans(
    session: SessionDep,
    company_id: uuid.UUID,
    month: MonthString | None = None,
    status: PlanStatus | None = None,
    scope_type: ScheduleScopeType | None = None,
    keyword: Keyword = None,
    skip: Skip = 0,
    limit: Limit = 100,
) -> Any:
    """List company plans; the rules page uses this to pick an override target."""
    return plan_service.list_schedule_plans(
        session,
        company_id=company_id,
        month=month,
        status=status,
        scope_type=scope_type,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{plan_id}/rule-overrides",
    response_model=PlanRuleOverridesPublic,
    responses=ERROR_RESPONSES,
)
def read_plan_rule_overrides(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """Return overrides, the effective rule, and the company default."""
    return rule_service.get_plan_rule_overrides(session, plan_id)


@router.put(
    "/{plan_id}/rule-overrides",
    response_model=PlanRuleOverridesPublic,
    responses=ERROR_RESPONSES,
)
def update_plan_rule_overrides(
    session: SessionDep,
    plan_id: uuid.UUID,
    overrides_in: PlanRuleOverridesUpdate,
) -> Any:
    """Replace plan overrides wholesale; ``null`` means inherit."""
    return rule_service.update_plan_rule_overrides(session, plan_id, overrides_in)
