import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep, attendance_access
from app.core.errors import ErrorResponse
from app.enums import PlanStatus, ScheduleScopeType
from app.models import Message
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.scheduling import (
    PlanCopyPreview,
    PlanCopyRequest,
    PlanRuleOverridesPublic,
    PlanRuleOverridesUpdate,
    SchedulePlanCreate,
    SchedulePlanMutationPublic,
    SchedulePlanPreview,
    SchedulePlanPreviewRequest,
    SchedulePlanPublic,
    SchedulePlansPublic,
    SchedulePlanUpdate,
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


@router.post(
    "/preview",
    response_model=SchedulePlanPreview,
    responses=ERROR_RESPONSES,
)
def preview_schedule_plan(
    session: SessionDep, plan_in: SchedulePlanPreviewRequest
) -> Any:
    """Dry-run a plan save: scope conflicts, roster impact, and time warnings."""
    return plan_service.preview_schedule_plan(session, plan_in)


@router.post(
    "/",
    response_model=SchedulePlanPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_schedule_plan(session: SessionDep, plan_in: SchedulePlanCreate) -> Any:
    """Create a plan, save its children, and expand its month in one transaction."""
    return plan_service.create_schedule_plan(session, plan_in)


@router.get(
    "/{plan_id}", response_model=SchedulePlanPublic, responses=ERROR_RESPONSES
)
def read_schedule_plan(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """Get one plan with its scopes and per-day shifts."""
    return plan_service.get_schedule_plan(session, plan_id)


@router.patch(
    "/{plan_id}", response_model=SchedulePlanPublic, responses=ERROR_RESPONSES
)
def update_schedule_plan(
    session: SessionDep,
    plan_id: uuid.UUID,
    plan_in: SchedulePlanUpdate,
) -> Any:
    """Replace supplied children wholesale and re-expand the month."""
    return plan_service.update_schedule_plan(session, plan_id, plan_in)


@router.post(
    "/{plan_id}/expand-preview",
    response_model=SchedulePlanPreview,
    responses=ERROR_RESPONSES,
)
def expand_preview(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """Dry-run a full month re-expansion for one saved plan."""
    return plan_service.expand_preview(session, plan_id)


@router.post(
    "/{plan_id}/expand",
    response_model=SchedulePlanMutationPublic,
    responses=ERROR_RESPONSES,
)
def expand_schedule_plan(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """Re-expand the plan's month without touching manual exceptions."""
    return plan_service.expand_schedule_plan(session, plan_id)


@router.post(
    "/{plan_id}/archive",
    response_model=SchedulePlanMutationPublic,
    responses=ERROR_RESPONSES,
)
def archive_schedule_plan(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """Archive the plan and re-expand the month without it."""
    return plan_service.archive_schedule_plan(session, plan_id)


@router.post(
    "/{plan_id}/unarchive",
    response_model=SchedulePlanMutationPublic,
    responses=ERROR_RESPONSES,
)
def unarchive_schedule_plan(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """Reactivate an archived plan after shift and scope checks."""
    return plan_service.unarchive_schedule_plan(session, plan_id)


@router.delete("/{plan_id}", response_model=Message, responses=ERROR_RESPONSES)
def delete_schedule_plan(session: SessionDep, plan_id: uuid.UUID) -> Any:
    """Delete a plan only when no roster entry references it."""
    return plan_service.delete_schedule_plan(session, plan_id)


@router.post(
    "/{plan_id}/copy-preview",
    response_model=PlanCopyPreview,
    responses=ERROR_RESPONSES,
)
def copy_preview(
    session: SessionDep, plan_id: uuid.UUID, copy_in: PlanCopyRequest
) -> Any:
    """Preview copying the plan definition to the next natural month."""
    return plan_service.copy_preview(session, plan_id, copy_in)


@router.post(
    "/{plan_id}/copy",
    response_model=SchedulePlanPublic,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def copy_schedule_plan(
    session: SessionDep, plan_id: uuid.UUID, copy_in: PlanCopyRequest
) -> Any:
    """Copy the plan definition into the next month and expand it."""
    return plan_service.copy_schedule_plan(session, plan_id, copy_in)


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
